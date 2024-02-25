# Script to create searchable PDF from scan PDF or images using Azure Form Recognizer
# Required packages
# pip install --upgrade azure-ai-formrecognizer pymupdf
# ページの並び替えはこれを通す前に行うこと
# 実際のページ番号に合うように並び替える
# 出力された後は目次の作成を行う
import io
import argparse
import fitz
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient, AnalyzeResult
import splitPDFbySize
import functools
import re
import Clean
#このファイルに認証情報を保存する
import private

isKindle = True


def isV(line):
    if (line.polygon[2].x - line.polygon[0].x) > (
        line.polygon[2].y - line.polygon[0].y
    ):
        return False
    else:
        return True


azure_counter = 0


def Azure_OCR(PDF):

    def merge_ocr_results(list):
        def merge_page_r(dict1, dict2):
            dict1["pages"].extend(dict2["pages"])
            return dict1

        return functools.reduce(merge_page_r, list)

    def cAzure_OCR(PDF):
        global azure_counter
        azure_counter += 1
        # Running OCR using Azure Form Recognizer Read API
        print(f"Starting Azure Form Recognizer OCR process... #{azure_counter}")
        document_analysis_client = DocumentAnalysisClient(
            endpoint=private.endpoint, credential=AzureKeyCredential(private.key)
        )
        poller = document_analysis_client.begin_analyze_document(
            "prebuilt-read", document=PDF.tobytes()
        )
        ocr_results = poller.result()
        print(
            f"Azure Form Recognizer finished OCR text       #{azure_counter} text for  {len(ocr_results.pages)} pages."
        )

        return ocr_results

    splitted_doc_list = splitPDFbySize.split_file(PDF)
    ocr_result_list_dic = list(
        map(lambda x: cAzure_OCR(x).to_dict(), splitted_doc_list)
    )
    ocr_result_dic = merge_ocr_results(ocr_result_list_dic)
    ocr_result = AnalyzeResult.from_dict(ocr_result_dic)

    return ocr_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_file",
        type=str,
        help="Input PDF or image (jpg, jpeg, tif, tiff, bmp, png) file name",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=False,
        default="",
        help="Output PDF file name. Default: input_file + .ocr.pdf",
    )
    args = parser.parse_args()

    input_file = args.input_file
    if args.output:
        output_file = args.output
    else:
        output_file = input_file + ".ocr.pdf"

    # Loading input file
    print(f"Loading input file {input_file}")

    clean_doc = Clean.CleanPDF(input_file, isKindle)

    for page_id, page in enumerate(Azure_OCR(clean_doc).pages):
        current_page = clean_doc.load_page(page_id)
        # current_page.set_rotation(-90)
        scale = (
            current_page.rect.width / page.width
            + current_page.rect.height / page.height
        ) / 2

        font = fitz.Font("japan")
        fontsize = 15

        # 回転させてからを考える?
        for line in page.lines:
            # 句読点をフォーマット
            # 半角だと文字幅のずれの原因になる

            # 前後がどちらも数字の場合だけ置換しないで
            line.content = re.sub(r"(?<!\d)\.(?!\d)", "。", line.content)
            line.content = re.sub(r"(?<!\d),(?!\d)", "、", line.content)
            line.content = re.sub(r"(?<!\d)，(?!\d)", "、", line.content)
            line.content = re.sub(r"(?<!\d)．(?!\d)", "。", line.content)

            desired_text_height = (line.polygon[2].y - line.polygon[0].y) * scale
            actual_text_height = fontsize
            desired_text_width = (line.polygon[2].x - line.polygon[0].x) * scale
            actual_text_width = font.text_length(line.content, fontsize=fontsize)

            if isV(line):
                tw = fitz.TextWriter(current_page.rect)
                tw.append(
                    fitz.Point(line.polygon[0].x * scale, line.polygon[0].y * scale),
                    line.content,
                    fontsize=fontsize,
                    font=fitz.Font("japan"),
                )
                tw.write_text(
                    current_page,
                    render_mode=3,
                    morph=(
                        fitz.Point(
                            line.polygon[0].x * scale, line.polygon[0].y * scale
                        ),
                        fitz.Matrix(270).prescale(
                            (
                                desired_text_height
                                + (
                                    font.text_length("。", fontsize=fontsize)
                                    / 2  # 句読点が文末の時は，画像認識で検知できない句読点の真の端を句読点の長さを足す
                                    if line.content.endswith(("。", "、"))
                                    else 0
                                )
                            )
                            / actual_text_width,
                            desired_text_width / actual_text_height,
                        ),
                    ),
                )
            else:
                tw = fitz.TextWriter(current_page.rect)
                tw.append(
                    fitz.Point(line.polygon[3].x * scale, line.polygon[3].y * scale),
                    line.content,
                    fontsize=fontsize,
                    font=fitz.Font("japan"),
                )
                tw.write_text(
                    current_page,
                    render_mode=3,
                    morph=(
                        fitz.Point(
                            line.polygon[3].x * scale, line.polygon[3].y * scale
                        ),
                        fitz.Matrix(0).prescale(
                            (
                                desired_text_width
                                + (
                                    font.text_length("。", fontsize=fontsize)
                                    / 2  # 句読点が文末の時は，句読点の長さを足す
                                    if line.content.endswith(("。", "、"))
                                    else 0
                                )
                            )
                            / actual_text_width,
                            desired_text_height / actual_text_height,
                        ),
                    ),
                )

            if line.content.isdigit():
                if 1 <= int(line.content) and int(line.content) <= len(clean_doc):
                    current_page.insert_link(
                        {
                            "kind": fitz.LINK_GOTO,
                            "from": fitz.Rect(
                                line.polygon[0].x * scale,
                                line.polygon[0].y * scale,
                                line.polygon[2].x * scale,
                                line.polygon[2].y * scale,
                            ),
                            "page": int(line.content) - 1,
                        }
                    )
            # Azureの認識した領域
            # current_page.draw_rect(
            #     fitz.Rect(
            #         fitz.Point(line.polygon[0].x * scale, line.polygon[0].y * scale),
            #         fitz.Point(line.polygon[2].x * scale, line.polygon[2].y * scale),
            #     )
            # )
    clean_doc.save(output_file)
    clean_doc.close()

    print(f"Searchable PDF is created: {output_file}")

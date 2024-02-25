import fitz


def flatten_list(lst):
    flat_list = []
    for item in lst:
        if isinstance(item, list):
            flat_list.extend(flatten_list(item))
        else:
            flat_list.append(item)
    return flat_list


def split_file(pdf_document):
    def split_file_r(pdf_document):
        # 目標サイズに応じて変更
        MAX_SIZE = 500000000
        # MAX_SIZE = 100
        if len(pdf_document.tobytes()) > MAX_SIZE:
            lastpage = len(pdf_document)
            # 1ページに達したら終了
            if lastpage == 1 or lastpage == 2:
                return [pdf_document]
            # 真ん中で分割するためのページ
            split = lastpage // 2
            # ファイル名生成 suffixはお好みで
            new_pdf1 = fitz.open()
            new_pdf2 = fitz.open()
            # 1ページづつwriterに追加
            new_pdf1.insert_pdf(pdf_document, to_page=split)
            new_pdf2.insert_pdf(pdf_document, from_page=split + 1)

            return [
                (
                    split_file_r(new_pdf1)
                    if len(new_pdf1.tobytes()) > MAX_SIZE
                    else new_pdf1
                ),
                (
                    split_file_r(new_pdf2)
                    if len(new_pdf2.tobytes()) > MAX_SIZE
                    else new_pdf2
                ),
            ]

        else:
            return [pdf_document]

    nested_list = split_file_r(pdf_document)
    return flatten_list(nested_list)


if __name__ == "__main__":
    # 例としてhoge.pdfを分割したいとする
    hoge = split_file(fitz.open("sample.pdf"))
    print(hoge)

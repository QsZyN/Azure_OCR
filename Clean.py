import fitz
import io


def CleanPDF(origin_path, isKindle):
    origin_doc = fitz.open(origin_path)
    clena_doc = fitz.open()

    page = origin_doc.load_page(0)
    image_list = page.get_images(full=True)
    img = image_list[0]
    rect = page.get_image_bbox(img)

    for page_number in range(len(origin_doc)):
        page = origin_doc.load_page(page_number)
        image_list = page.get_images(full=True)
        clea_page = clena_doc.new_page(width=page.rect.width, height=page.rect.height)
        if image_list:

            img = image_list[0]

            if not isKindle:
                rect = page.get_image_bbox(img)

            xref = img[0]
            base_image = origin_doc.extract_image(xref)
            image_bytes = base_image["image"]
            # 比率を維持しないようにしないと，最悪PDFから画像が外れる
            clea_page.insert_image(
                rect, stream=io.BytesIO(image_bytes), keep_proportion=False
            )

    return clena_doc


if __name__ == "__main__":
    clena_doc = CleanPDF(
        "sample.pdf",
        True,
    )
    clena_doc.save("ocr_result.pdf")
    clena_doc.close()

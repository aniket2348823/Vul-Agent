try:
    from pypdf import PdfReader
    reader = PdfReader('test3.pdf')
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    with open('dump.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Done")
except ImportError:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader('test3.pdf')
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        with open('dump.txt', 'w', encoding='utf-8') as f:
            f.write(text)
        print("Done")
    except Exception as e:
        print("Failed to parse", e)

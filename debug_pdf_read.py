import fitz

filepath = "/workspaces/TG_Hire/LOGO/CVS/68dc09195bb8b.pdf"
try:
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    print(text[:500])
except Exception as e:
    print(e)

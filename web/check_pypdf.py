
import PyPDF2
print(f"PyPDF2 Version: {PyPDF2.__version__}")
try:
    reader = PyPDF2.PdfFileReader
    print("PdfFileReader exists.")
except AttributeError:
    print("PdfFileReader does NOT exist (likely v3.0+).")

from docxtpl import DocxTemplate, InlineImage
from graf import createGraf

def render_docx_template(file, columns, value):
    doc = DocxTemplate("templates/docx/%s.docx" % (file))
    context = generate_context(columns, value)
 
    if file == 'books_udk': # Костыль ))))
        createGraf(value)
        context['graf'] = InlineImage(doc, image_descriptor='static/Image/tmp/graf.png')

    doc.render(context)
    doc.save('output_report/%s.docx' % (file))
    return 'output_report/%s.docx' % (file)

def generate_context(keys, values):
    context = {
        'col_labels': keys,
        'tbl_contents': [{'cols': list(value)} for value in values]
    }
    return context
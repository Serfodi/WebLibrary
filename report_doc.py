from docxtpl import DocxTemplate

def render_docx_template(file, columns, value):
    patch = "templates/docx/%s.docx" % (file)
    doc = DocxTemplate(patch)
    context = generate_context(columns, value)
    doc.render(context)
    doc.save('output_report/%s' % (file))
    return patch

def generate_context(keys, values):
    context = {
        'col_labels': keys,
        'tbl_contents': [{'cols': list(value)} for value in values]
    }
    return context
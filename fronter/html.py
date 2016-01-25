from fronter import *

unescape = HTMLParser().unescape


def to_file(xml, add_meta=False):
    fd, fname = mkstemp(prefix='fronter_', suffix='.html')

    string  = '' if not add_meta else \
              '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\n'
    string += re.sub('</?div.*?>', '', unescape(tostring(xml).decode('utf-8')))

    with os.fdopen(fd, 'wb') as f:
        f.write(string.encode('utf-8'))
    return fname


def to_text(xml):

    content = ''
    for elem in xml:

        if elem.tag == 'table':
            rows = []
            try:
                for tr in elem:
                    rows.append([td.text_content().strip() for td in tr])

                widths = list(map(max, [map(len, clm) for clm in zip(*rows)]))
                pieces = ['%-' + str(w + 2) + 's' for w in widths]

                table_content = '\n' + '-' * (sum(widths) + 4 + 2*len(widths)) + '\n'
                for row in rows:
                    table_content += '| ' + ''.join(pieces) % tuple(row) + ' |\n'
                table_content += '-' * (sum(widths) + 4 + 2*len(widths)) + '\n'

                content += table_content
            except:
                content += col('!! badass table', c.ERR)

        elif elem.tag == 'ul':
            content += '\n'
            for li in elem:
                content += ' * ' + li.text_content() + '\n'
            content += '\n'

        elif elem.tag == 'ol':
            content += '\n'
            for i, li in enumerate(elem):
                content += ' %i. ' % (i + 1) + li.text_content() + '\n'
            content += '\n'

        else:
            content += elem.text_content()

        # Trailing text after <br> etc ...
        content += elem.tail or ''

    return wrap(content)

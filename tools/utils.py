from argparse import ArgumentParser, RawDescriptionHelpFormatter


def create_parser(usage='%(prog)s [options]',
                  description='',
                  formatter_class=None):
    formatter_class = formatter_class or RawDescriptionHelpFormatter
    return ArgumentParser(usage=usage, description=description, formatter_class=formatter_class)


def build_parser():
    description = (
        'Mobius'
        '\n'
        '\n'
        'Example:'
        '\n'
        "      fabfed -c config.yaml -apply"
        '\n'
    )

    parser = create_parser(description=description)
    parser.add_argument('-c', '--config', type=str, default='', help='yaml config file', required=True)
    parser.add_argument('-apply', action='store_true', default=False, help='create resources')
    parser.add_argument('-destroy', action='store_true', default=False, help='delete resources')
    return parser

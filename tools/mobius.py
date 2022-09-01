from . import utils
import sys

from mobius.controller.controller import Controller


# noinspection PyArgumentList
def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = utils.build_parser()
    args = parser.parse_args(argv)
    print(args)

    if args.apply:
        controller = Controller(config_file_location=args.config)
        controller.create()
        resources = controller.get_resources()

        for r in resources:
            print(r)
            print(r.list_nodes())
    elif args.destroy:
        raise Exception("not implemented yet")


if __name__ == "__main__":
    main(sys.argv[1:])

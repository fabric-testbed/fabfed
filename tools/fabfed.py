import sys

from fabfed.controller.controller import Controller
from fabfed.model.state import *
from . import utils


# noinspection PyArgumentList
def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = utils.build_parser()
    args = parser.parse_args(argv)
    print(args)

    if args.apply:
        controller = Controller(config_file_location=args.config)
        controller.create()
        states = controller.get_states()

        with open("output.yml", "w") as stream:
            stream.write(yaml.dump(states, Dumper=get_dumper()))

        slice_objects = controller.get_slices()

        for slice_object in slice_objects:
            print(slice_object)
            print(slice_object.list_nodes())

    if args.show:
        with open("output.yml", 'r') as stream:
            obj = yaml.load(stream, Loader=get_loader())

            print(obj)

    if args.destroy:
        controller = Controller(config_file_location=args.config)

        with open("output.yml", 'r') as stream:
            provider_states = yaml.load(stream, Loader=get_loader())

        controller.delete(provider_states=provider_states)


if __name__ == "__main__":
    main(sys.argv[1:])

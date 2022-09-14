import sys

from fabfed.controller.controller import Controller
from fabfed.util.config import Config
from fabfed.controller.provider_factory import default_provider_factory
from . import utils


def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = utils.build_parser()
    args = parser.parse_args(argv)
    logger = utils.init_looger()

    if args.apply:
        config = Config(file_name=args.config)
        controller = Controller(config=config, logger=logger)
        controller.init(default_provider_factory)

        try:
            controller.plan()
            controller.create()
            states = controller.get_states()
            utils.save_states(states, args.friendly_name)
        except Exception as e:
            raise e

        slice_objects = controller.get_slices()

        for slice_object in slice_objects:
            print(slice_object)
            print(slice_object.list_networks())
            print(slice_object.list_nodes())

    if args.plan:
        config = Config(file_name=args.config)
        controller = Controller(config=config, logger=logger)
        controller.init(default_provider_factory)
        controller.plan()
        states = controller.get_states()
        utils.dump_states(states, args.json)

    if args.show:
        states = utils.load_states(args.friendly_name)
        utils.dump_states(states, args.json)

    if args.destroy:
        controller = None

        try:
            states = utils.load_states(args.friendly_name)

            if states:
                config = Config(file_name=args.config)
                controller = Controller(config=config, logger=logger)
                controller.init(default_provider_factory)
                controller.delete(provider_states=states)
        except Exception as e:
            raise e

        if controller:
            states = controller.get_states()
            utils.save_states(states, args.friendly_name)


if __name__ == "__main__":
    main(sys.argv[1:])

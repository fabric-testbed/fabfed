import sys

from fabfed.controller.controller import Controller
from fabfed.util.config import Config
from fabfed.controller.provider_factory import default_provider_factory
from fabfed.util import utils


def manage_workflow(args):
    logger = utils.init_looger()

    var_dict = utils.load_vars(args.var_file) if args.var_file else {}

    if args.validate:
        Config(file_name=args.config, var_dict=var_dict)
        logger.info("config looks ok")
        return

    if args.apply:
        config = Config(file_name=args.config, var_dict=var_dict)
        controller = Controller(config=config, logger=logger)
        controller.init(default_provider_factory)

        try:
            controller.plan()
            controller.create()
            states = controller.get_states()
            utils.save_states(states, args.session_name)
        except Exception as e:
            raise e

        slice_objects = controller.get_slices()

        for slice_object in slice_objects:
            print(slice_object)
            print(slice_object.list_networks())
            print(slice_object.list_nodes())
        return

    if args.plan:
        config = Config(file_name=args.config, var_dict=var_dict)
        controller = Controller(config=config, logger=logger)
        controller.init(default_provider_factory)
        controller.plan()
        states = controller.get_states()
        utils.dump_states(states, args.json)
        return

    if args.show:
        states = utils.load_states(args.session_name)
        utils.dump_states(states, args.json)
        return

    if args.destroy:
        controller = None

        try:
            states = utils.load_states(args.session_name)

            if states:
                config = Config(file_name=args.config, var_dict=var_dict)
                controller = Controller(config=config, logger=logger)
                controller.init(default_provider_factory)
                controller.delete(provider_states=states)
        except Exception as e:
            raise e

        if controller:
            states = controller.get_states()
            utils.save_states(states, args.session_name)
        return


def manage_sessions(args):
    if args.show:
        utils.dump_sessions(args.json)
        return


def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = utils.build_parser(manage_workflow=manage_workflow, manage_sessions=manage_sessions)
    args = parser.parse_args(argv)

    if len(args.__dict__) == 0:
        parser.print_usage()
        sys.exit(1)

    args.dispatch_func(args)


if __name__ == "__main__":
    main(sys.argv[1:])

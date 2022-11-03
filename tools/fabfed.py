import sys

from fabfed.controller.controller import Controller
from fabfed.util.config import Config
from fabfed.controller.provider_factory import default_provider_factory
from fabfed.util import utils


def manage_workflow(args):
    logger = utils.init_looger()

    var_dict = utils.load_vars(args.var_file) if args.var_file else {}

    if args.validate:
        try:
            Config(dir_path=args.config_dir, var_dict=var_dict)
            logger.info("config looks ok")
        except Exception as e:
            logger.error(f"Validation failed .... {type(e)} {e}")
            sys.exit(1)

    if args.apply:
        config = Config(dir_path=args.config_dir, var_dict=var_dict)

        try:
            controller = Controller(config=config, logger=logger)
        except Exception as e:
            logger.error(f"Exceptions while initializing controller .... {e}")
            sys.exit(1)

        try:
            controller.init(session=args.session, provider_factory=default_provider_factory)
        except Exception as e:
            logger.error(f"Exceptions while initializing providers  .... {e}")
            sys.exit(1)

        try:
            controller.plan()
        except Exception as e:
            logger.error(f"Exceptions while adding resources .... {e}")

        try:
            controller.create()
        except Exception as e:
            logger.error(f"Exceptions while creating resources .... {e}")

        states = controller.get_states()
        utils.save_states(states, args.session)

        pending = 0
        nodes = 0
        networks = 0
        services = 0
        failed = 0

        for state in states:
            pending += len(state.pending)
            nodes += len(state.node_states)
            networks += len(state.network_states)
            services += len(state.service_states)
            failed += len(state.failed)

        logger.info(f"nodes={nodes}, networks={networks}, services={services}, pending={pending}, failed={failed}")
        return

    if args.plan:
        config = Config(dir_path=args.config_dir, var_dict=var_dict)
        controller = Controller(config=config, logger=logger)
        controller.init(session=args.session, provider_factory=default_provider_factory)
        controller.plan()
        states = controller.get_states()
        utils.dump_states(states, args.json)
        return

    if args.show:
        states = utils.load_states(args.session)
        utils.dump_states(states, args.json)
        return

    if args.summary:
        states = utils.load_states(args.session)
        temp = []

        for provider_state in states:
            for node_state in provider_state.node_states:
                attributes = dict()
                props = ['mgmt_ip', 'username', 'site', 'state', 'id']

                for prop in props:
                    attributes[prop] = node_state.attributes[prop]
                node_state.attributes = attributes
                temp.append(node_state)

        utils.dump_states(temp, args.json)
        return

    if args.destroy:
        states = utils.load_states(args.session)

        try:
            if states:
                config = Config(dir_path=args.config_dir, var_dict=var_dict)
                controller = Controller(config=config, logger=logger)
                controller.init(session=args.session, provider_factory=default_provider_factory)
                controller.delete(provider_states=states)
        except Exception as e:
            logger.error(f"We have exceptions .... {type(e)} {e}")
            import traceback

            logger.error(traceback.format_exc())

        utils.save_states(states, args.session)
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

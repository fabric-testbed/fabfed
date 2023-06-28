import sys

from fabfed.controller.controller import Controller
from fabfed.controller.provider_factory import default_provider_factory
from fabfed.exceptions import ControllerException
from fabfed.util import utils
from fabfed.util import state as sutil
from fabfed.util.config import WorkflowConfig


def manage_workflow(args):
    logger = utils.init_logger()

    config_dir = utils.absolute_path(args.config_dir)
    config_dir_from_meta = sutil.load_meta_data(args.session, 'config_dir')

    if config_dir_from_meta and config_dir_from_meta != config_dir:
        logger.error(f"attempt to use fabfed session {args.session} from the wrong config dir {config_dir} ...")
        logger.warning(f"ATTN: The CORRECT config dir for session {args.session} is {config_dir_from_meta}!!!!!!!")
        sys.exit(1)

    sutil.save_meta_data(dict(config_dir=config_dir), args.session)
    var_dict = utils.load_vars(args.var_file) if args.var_file else {}

    from fabfed.controller.policy_helper import load_policy

    policy = load_policy(policy_file=args.policy_file) if args.policy_file else {}

    if args.validate:
        try:
            WorkflowConfig(dir_path=config_dir, var_dict=var_dict)
            logger.info("config looks ok")
        except Exception as e:
            logger.error(f"Validation failed .... {type(e)} {e}")
            logger.error(e, exc_info=True)
            sys.exit(1)

    if args.apply:
        config = WorkflowConfig(dir_path=config_dir, var_dict=var_dict)

        try:
            controller = Controller(config=config, logger=logger, policy=policy)
        except Exception as e:
            logger.error(f"Exceptions while initializing controller .... {e}")
            sys.exit(1)

        try:
            controller.init(session=args.session, provider_factory=default_provider_factory)
        except Exception as e:
            logger.error(f"Exceptions while initializing providers  .... {e}")
            sys.exit(1)

        states = sutil.load_states(args.session)

        try:
            controller.plan(provider_states=states)
        except ControllerException as e:
            logger.error(f"Exceptions while adding resources ... {e}")
        except Exception as e:
            logger.error(f"Exceptioin while planning ... {e}")
        except KeyboardInterrupt as kie:
            logger.error(f"Keyboard Interrupt while adding  resources ... {kie}")
            sys.exit(1)

        try:
            controller.create(provider_states=states)
        except KeyboardInterrupt as kie:
            logger.error(f"Keyboard Interrupt while creating resources ... {kie}")
        except ControllerException as ce:
            logger.error(f"Exceptions while creating resources ... {ce}")

        states = controller.get_states()
        pending = 0
        nodes = 0
        networks = 0
        services = 0
        failed = 0

        for state in states:
            pending += len(state.pending)
            pending += len(state.pending_internal)
            nodes += len([n for n in state.node_states if n.label not in state.failed])
            networks += len([n for n in state.network_states if n.label not in state.failed])
            services += len([s for s in state.service_states if s.label not in state.failed])
            failed += len(state.failed)

        logger.info(f"nodes={nodes}, networks={networks}, services={services}, pending={pending}, failed={failed}")
        sutil.save_states(states, args.session)
        return

    if args.init:
        config = WorkflowConfig(dir_path=config_dir, var_dict=var_dict)
        controller = Controller(config=config, logger=logger, policy=policy)
        controller.init(session=args.session, provider_factory=default_provider_factory)
        sutil.dump_resources(resources=controller.resources, to_json=args.json, summary=args.summary)
        return

    if args.plan:
        config = WorkflowConfig(dir_path=config_dir, var_dict=var_dict)
        controller = Controller(config=config, logger=logger, policy=policy)
        controller.init(session=args.session, provider_factory=default_provider_factory)
        states = sutil.load_states(args.session)

        try:
            controller.plan(provider_states=states)
        except ControllerException as e:
            logger.error(f"Exceptions while adding resources ... {e}")

        states = controller.get_states()
        sutil.dump_states(states, args.json, args.summary)
        return

    if args.show:
        states = sutil.load_states(args.session)
        sutil.dump_states(states, args.json, args.summary)
        return

    if args.destroy:
        states = sutil.load_states(args.session)

        try:
            if states:
                config = WorkflowConfig(dir_path=config_dir, var_dict=var_dict)
                controller = Controller(config=config, logger=logger, policy=policy)
                controller.init(session=args.session, provider_factory=default_provider_factory)
                controller.delete(provider_states=states)

            if not states:
                sutil.destroy_session(args.session)
                return
        except ControllerException as e:
            logger.error(f"Exceptions while deleting resources ...{e}")
            import traceback

            logger.error(traceback.format_exc())

        sutil.save_states(states, args.session)
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

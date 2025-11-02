import sys
import long_dist_sim_with_box as lds


def main(argv=None):
    """Entry point forwarding CLI arguments to the simulation."""

    lds.main(argv)


if __name__ == "__main__":
    main(sys.argv[1:])

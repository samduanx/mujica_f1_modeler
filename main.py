import sys
import src.simulation.enhanced_long_dist_sim as elds


def main(argv=None):
    """Entry point forwarding CLI arguments to the simulation."""

    elds.main(argv)


if __name__ == "__main__":
    main(sys.argv[1:])

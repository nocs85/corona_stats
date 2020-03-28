#!/usr/bin/env python3

import argparse
from app.core import engine
from datetime import datetime
import matplotlib.pyplot as plt

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plots transnational covid-19 statistics.')

    # optionally provide the limit date (by default today)
    parser.add_argument('--limitDate', type=engine.iso8601YmdValidator, required=False,
                        help='target date for italian data (Y-m-d ISO-8601 format)',
                        default=datetime.now().strftime(engine.DATE_FORMAT))
    args = parser.parse_args()

    # generate graphs
    engine.processData(args.limitDate.strftime(engine.DATE_FORMAT))
    engine.processData(args.limitDate.strftime(engine.DATE_FORMAT),isDeaths=True)
    # plot them
    plt.show()


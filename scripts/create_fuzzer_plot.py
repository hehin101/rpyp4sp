#!/usr/bin/env python3

import os
import argparse
import matplotlib.pyplot as plt

def find_iteration_and_total(line):
    iteration_start = line.find("iteration ") + len("iteration ")
    iteration_end = line.find(":")
    iteration = int(line[iteration_start:iteration_end])
    total_start = line.find("total ") + len("total ")
    total_end = line.find(")", total_start)
    total = int(line[total_start:total_end])
    return iteration, total

def data_from_log(fuzzer_log):
    data = {"hit": [], "miss": [], "error_hit": [], "error_miss": []}
    with open(fuzzer_log) as file:
        for line in file:
            if line.startswith("NEW HIT"):
                data["hit"].append(find_iteration_and_total(line))
            elif line.startswith("NEW MISS"):
                data["miss"].append(find_iteration_and_total(line))
            elif line.startswith("NEW ERROR HIT"):
                data["error_hit"].append(find_iteration_and_total(line))
            elif line.startswith("NEW ERROR MISS"):
                data["error_miss"].append(find_iteration_and_total(line))
    return data

def plot_data(data, plot_file):
    plt.figure("Fuzzer plot", figsize=(16,9))
    hit_x, hit_y = zip(*data["hit"])
    plt.plot(hit_x, hit_y, label="new hits")
    miss_x, miss_y = zip(*data["miss"])
    plt.plot(miss_x, miss_y, label="new misses")
    error_hit_x, error_hit_y = zip(*data["error_hit"])
    plt.plot(error_hit_x, error_hit_y, label="new error hits")
    error_miss_x, error_miss_y = zip(*data["error_miss"])
    plt.plot(error_miss_x, error_miss_y, label="new error misses")
    plt.xlabel("Iterations")
    plt.ylabel("Amount")
    plt.legend(loc='upper left')
    plt.savefig(plot_file, bbox_inches='tight')

def main(args):
    assert os.path.exists(args.fuzzer_log)
    data = data_from_log(args.fuzzer_log)
    plot_data(data, args.output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-fl", "--fuzzer-log", help="path to fuzzer log file",
                        type=str, default="./fuzz.log")
    parser.add_argument("-o", "--output", help="path to output file",
                        type=str, default="./fuzz_plot.png")
    args = parser.parse_args()
    main(args)

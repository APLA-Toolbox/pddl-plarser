from common import get_all_pddl_from_data, plot_data, scatter_data
from os import path
import sys
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import logging
from jupyddl.automated_planner import AutomatedPlanner


def gather_data_astar(domain_path="", problem_path="", heuristic_key="goal_count"):
    has_multiple_files_tested = True
    if not domain_path and not problem_path:
        has_multiple_files_tested = False
        metrics = dict()
        for problem, domain in get_all_pddl_from_data():
            logging.debug("Loading new PDDL instance planned with A*...")
            logging.debug("Domain: " + domain)
            logging.debug("Problem: " + problem)
            apla = AutomatedPlanner(domain, problem)
            if heuristic_key in apla.available_heuristics:
                _, total_time, opened_nodes = apla.astar_best_first_search(
                    heuristic=apla.available_heuristics[heuristic_key]
                )
            else:
                logging.critical(
                    "Heuristic is not implemented! (Key not found in registered heuristics dict)"
                )
                return [0], [0], has_multiple_files_tested
            metrics[total_time] = opened_nodes

        total_nodes = list(metrics.values())
        times = list(metrics.keys())
        return times, total_nodes, has_multiple_files_tested
    logging.debug("Loading new PDDL instance...")
    logging.debug("Domain: " + domain_path)
    logging.debug("Problem: " + problem_path)
    apla = AutomatedPlanner(domain_path, problem_path)
    if heuristic_key in apla.available_heuristics:
        _, total_time, opened_nodes = apla.astar_best_first_search(
            heuristic=apla.available_heuristics[heuristic_key]
        )
    else:
        logging.critical(
            "Heuristic is not implemented! (Key not found in registered heuristics dict)"
        )
        return [0], [0], has_multiple_files_tested
    return [total_time], [total_nodes], has_multiple_files_tested


def plot_astar_data(heuristic_key="goal_count", domain="", problem=""):
    if bool(not problem) != bool(not domain):
        logging.warning(
            "Either problem or domain wasn't provided, testing all files in data folder"
        )
        problem = domain = ""
    times, total_nodes, has_multiple_files_tested = gather_data_astar(
        heuristic_key=heuristic_key, problem_path=problem, domain_path=domain
    )
    title = "A* Statistics" + "[Heuristic: " + heuristic_key + "]"
    if has_multiple_files_tested:
        plot_data(times, total_nodes, title)
    else:
        scatter_data(times, total_nodes, title)


if __name__ == "__main__":
    plot_astar_data()

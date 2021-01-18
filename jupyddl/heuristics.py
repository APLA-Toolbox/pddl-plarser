import logging


class BasicHeuristic:
    def __init__(self, automated_planner, heuristic_key):
        self.automated_planner = automated_planner
        self.heuristic_keys = {
            "basic/zero": self.__zero_heuristic,
            "basic/goal_count": self.__goal_count_heuristic,
        }
        if heuristic_key not in list(self.heuristic_keys.keys()):
            logging.warning(
                "Heuristic key isn't registered, forcing it to [basic/goal_count]"
            )
            heuristic_key = "basic/goal_count"

        self.current_h = heuristic_key

    def compute(self, state):
        return self.heuristic_keys[self.current_h](state)

    def __zero_heuristic(self, state):
        return 0

    def __goal_count_heuristic(self, state):
        count = 0
        for goal in self.automated_planner.goals:
            if not self.automated_planner.state_has_term(state, goal):
                count += 1
        return count


class DeleteRelaxationHeuristic:
    def __init__(self, automated_planner, heuristic_key):
        class DRHCache:
            def __init__(self, domain=None, axioms=None, preconds=None, additions=None):
                self.domain = domain
                self.axioms = axioms
                self.preconds = preconds
                self.additions = additions

        self.automated_planner = automated_planner
        self.cache = DRHCache()
        self.heuristic_keys = {
            "delete_relaxation/h_add": self.__h_add,
            "delete_relaxation/h_max": self.__h_max,
        }
        if heuristic_key not in list(self.heuristic_keys.keys()):
            logging.warning(
                "Heuristic key isn't registered, forcing it to [delete_relaxation/h_add]"
            )
            heuristic_key = "delete_relaxation/h_add"

        self.current_h = heuristic_key
        self.has_been_precomputed = False
        self.__pre_compute()
        # return self.heuristic_keys[self.current_h](state)

    def compute(self, state):
        if not self.has_been_precomputed:
            self.__pre_compute()
        domain = self.cache.domain
        goals = self.automated_planner.goals
        types = state.types
        facts = state.facts
        fact_costs = self.automated_planner.pddl.init_facts_costs(facts)
        while True:
            facts, state = self.automated_planner.pddl.get_facts_and_state(
                fact_costs, types
            )
            if self.automated_planner.satisfies(goals, state):
                costs = []
                fact_costs_str = dict([(str(k), val) for k, val in fact_costs.items()])
                for g in goals:
                    if str(g) in fact_costs_str:
                        costs.append(fact_costs_str[str(g)])
                costs.insert(0, 0)
                return self.heuristic_keys[self.current_h](costs)

            for ax in self.cache.axioms:
                fact_costs = self.automated_planner.pddl.compute_costs_one_step_derivation(
                    facts, fact_costs, ax, self.current_h
                )

            actions = self.automated_planner.available_actions(state)
            for act in actions:
                fact_costs = self.automated_planner.pddl.compute_cost_action_effect(
                    fact_costs, act, domain, self.cache.additions, self.current_h
                )

            if len(fact_costs) == self.automated_planner.pddl.length(
                facts
            ) and self.__facts_eq(fact_costs, facts):
                break

        return float("inf")

    def __pre_compute(self):
        if self.has_been_precomputed:
            return
        domain = self.automated_planner.domain
        domain, axioms = self.automated_planner.pddl.compute_hsp_axioms(domain)
        # preconditions = dict()
        additions = dict()
        self.automated_planner.pddl.cache_global_preconditions(domain)
        for name, definition in domain.actions.items():
            additions[name] = self.automated_planner.pddl.effect_diff(
                definition.effect
            ).add
        self.cache.additions = additions
        self.cache.preconds = self.automated_planner.pddl.g_preconditions
        self.cache.domain = domain
        self.cache.axioms = axioms
        self.has_been_precomputed = True

    def __h_add(self, costs):
        return sum(costs)

    def __h_max(self, costs):
        return max(costs)

    def __facts_eq(self, facts_dict, facts_set):
        fact_costs_str = dict([(str(k), val) for k, val in facts_dict.items()])
        for f in facts_set:
            if not (str(f) in fact_costs_str.keys()):
                return False
        return True


class CriticalPathHeuristic:
    def __init__(self, automated_planner, critical_path_level=1):
        class CPCache:
            def __init__(self, domain=None, axioms=None, preconds=None, additions=None):
                self.domain = domain
                self.axioms = axioms
                self.preconds = preconds
                self.additions = additions

        self.automated_planner = automated_planner
        self.cache = CPCache()
        if critical_path_level > 3:
            logging.warning(
                "Critical Path level is only implemented until 3, forcing it to 3."
            )
            self.critical_path_level = 3
        if critical_path_level < 1:
            logging.warning(
                "Critical Path level has to be at least 1, forcing it to 1."
            )
            self.critical_path_level = 1
        else:
            self.critical_path_level = critical_path_level
        self.has_been_precomputed = False
        self.__pre_compute()
        # return self.heuristic_keys[self.current_h](state)

    def compute(self, state):
        if not self.has_been_precomputed:
            self.__pre_compute()
        domain = self.cache.domain
        goals = self.automated_planner.goals
        types = state.types
        facts = state.facts
        fact_costs = self.automated_planner.pddl.init_facts_costs(facts)
        while True:
            facts, state = self.automated_planner.pddl.get_facts_and_state(
                fact_costs, types
            )
            if self.automated_planner.satisfies(goals, state):
                costs = []
                fact_costs_str = dict([(str(k), val) for k, val in fact_costs.items()])
                if self.critical_path_level == 1:
                    for g in goals:
                        if str(g) in fact_costs_str:
                            costs.append(fact_costs_str[str(g)])
                if self.critical_path_level == 2:
                    pairs_of_goals = [
                        (g1, g2) for g1 in goals for g2 in goals if g1 != g2
                    ]
                    for gs in pairs_of_goals:
                        if (
                            str(gs[0]) in fact_costs_str
                            and str(gs[1]) in fact_costs_str
                        ):
                            costs.append(
                                fact_costs_str[str(gs[0])] + fact_costs_str[str(gs[1])]
                            )
                if self.critical_path_level == 3:
                    triplets_of_goals = [
                        (g1, g2, g3)
                        for g1 in goals
                        for g2 in goals
                        for g3 in goals
                        if g1 != g2 and g1 != g3 and g2 != g3
                    ]
                    for gs in triplets_of_goals:
                        if (
                            str(gs[0]) in fact_costs_str
                            and str(gs[1]) in fact_costs_str
                            and str(gs[2]) in fact_costs_str
                        ):
                            costs.append(
                                fact_costs_str[str(gs[0])]
                                + fact_costs_str[str(gs[1])]
                                + fact_costs_str[str(gs[2])]
                            )
                costs.insert(0, 0)
                return max(costs)

            for ax in self.cache.axioms:
                fact_costs = self.automated_planner.pddl.compute_costs_one_step_derivation(
                    facts, fact_costs, ax, "max"
                )

            actions = self.automated_planner.available_actions(state)
            for act in actions:
                fact_costs = self.automated_planner.pddl.compute_cost_action_effect(
                    fact_costs, act, domain, self.cache.additions, "max"
                )

            if len(fact_costs) == self.automated_planner.pddl.length(
                facts
            ) and self.__facts_eq(fact_costs, facts):
                break

        return float("inf")

    def __pre_compute(self):
        if self.has_been_precomputed:
            return
        domain = self.automated_planner.domain
        domain, axioms = self.automated_planner.pddl.compute_hsp_axioms(domain)
        # preconditions = dict()
        additions = dict()
        self.automated_planner.pddl.cache_global_preconditions(domain)
        for name, definition in domain.actions.items():
            additions[name] = self.automated_planner.pddl.effect_diff(
                definition.effect
            ).add
        self.cache.additions = additions
        self.cache.preconds = self.automated_planner.pddl.g_preconditions
        self.cache.domain = domain
        self.cache.axioms = axioms
        self.has_been_precomputed = True

    def __h_add(self, costs):
        return sum(costs)

    def __h_max(self, costs):
        return max(costs)

    def __facts_eq(self, facts_dict, facts_set):
        fact_costs_str = dict([(str(k), val) for k, val in facts_dict.items()])
        for f in facts_set:
            if not (str(f) in fact_costs_str.keys()):
                return False
        return True

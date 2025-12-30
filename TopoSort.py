from __future__ import annotations
from typing import Any

from graphlib import TopologicalSorter


# Do a topological (partially ordered) sort.

# # Define the partial ordering (dependencies) as a dictionary:
# # Key = Task, Value = Set of tasks that must precede the Key task
#
# # The values can be anything as long as they are hashable
# dependencies = {
#     "Task_D": {"Task_A", "Task_C"},     # Task_D comes before Task_A or Task_C
#     "Task_B": {"Task_A"},
#     "Task_C": {"Task_A"},
#     "Task_A": set(),  # Task A has no prerequisites
#     "Task_E": {"Task_D"}
# }
#
# # 1. Create a TopologicalSorter instance
# # We invert the dictionary to represent it as a graph where the key
# # is a node and the values are its direct successors (which is the input
# # format expected by the sorter's .add() method).
# # Alternatively, we can use the graph directly and the sorter handles the logic.
#
# ts = TopologicalSorter(dependencies)
#
# # 2. Get the sorted order
# try:
#     # .static_order() returns an iterator for the topologically sorted nodes
#     ordered_tasks = list(ts.static_order())
#     print("The partial order can be resolved into this total order:")
#     print(ordered_tasks)
#
# except Exception as e:
#     # This happens if there is a

class Sorter:
    def __init__(self):
        self.dependencies={}        # This is an empty graph

    # Add a single ordered pair A<B
    def AddSingleOrdering(self, a: Any, b: Any):
        if a in self._dependencies.keys():
            self.dependencies[a].append(b)
        else:
            self.dependencies[a]={b}

    # Add an ordered list A<B,C,D...
    def AddMultipleOrdering(self, *args):
        for i in range(len(args)-1):
            self.AddSingleOrdering(args[i], args[i+1])

    def AddUnorderedSingleton(self, s: Any):
        if a not in self._dependencies.keys():
            self.dependencies[s]={}


    def Sort(self) -> list[Any]|None:

        ts = TopologicalSorter(self.dependencies)

        # Get the sorted order
        try:
            # .static_order() returns an iterator for the topologically sorted nodes
            ordered_tasks = list(ts.static_order())
            print("The partial order can be resolved into this total order:")
            print(ordered_tasks)
            return ordered_tasks

        except Exception as e:
            # This happens if there is a loop
            return  None# Do nothing
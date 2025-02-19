import random
import matplotlib.pyplot as plt
from collections import defaultdict
from itertools import combinations
import names
import numpy as np
import matplotlib

matplotlib.use('Agg')


class SeatingGenerator:
    def __init__(self, guests, table_size, num_tables, constraints):
        self.guests = guests
        self.table_size = table_size
        self.num_tables = num_tables
        self.constraints = self._process_constraints(constraints)
        self.must_groups = []
        self.group_conflicts = defaultdict(set)

    @staticmethod
    def _process_constraints(raw_constraints):
        constraints = defaultdict(lambda: {'must': False, 'must_not': False, 'prefer': False, 'prefer_apart': False})
        for a, b, constraint in raw_constraints:
            pair = frozenset({a, b})

            current = constraints[pair]
            if constraint in ['must', 'must_not']:
                if current[constraint]:
                    continue
                opposite = 'must' if constraint == 'must_not' else 'must_not'
                if current[opposite]:
                    raise ValueError(f"Conflicting constraints between {a} and {b}")

            constraints[pair][constraint] = True
        return constraints

    def _form_must_groups(self):
        parent = {}

        def find(u):
            while parent[u] != u:
                parent[u] = parent[parent[u]]
                u = parent[u]
            return u

        def union(u, v):
            root_u = find(u)
            root_v = find(v)
            if root_u != root_v:
                parent[root_v] = root_u

        parent = {guest: guest for guest in self.guests}
        for pair in self.constraints:
            if self.constraints[pair]['must']:
                a, b = tuple(pair)
                union(a, b)

        groups = defaultdict(set)
        for guest in self.guests:
            groups[find(guest)].add(guest)

        self.must_groups = list(groups.values())

        for group in self.must_groups:
            if len(group) > self.table_size:
                raise ValueError(f"Group {group} exceeds table size")

    def _build_group_conflicts(self):
        for (i, g1), (j, g2) in combinations(enumerate(self.must_groups), 2):
            if any(self.constraints[frozenset({a, b})]['must_not']
                   for a in g1 for b in g2):
                self.group_conflicts[i].add(j)
                self.group_conflicts[j].add(i)

    def _assign_groups_to_tables(self):
        sorted_groups = sorted(
            enumerate(self.must_groups),
            key=lambda x: (
                -len(x[1]),
                -len(self.group_conflicts[x[0]]),
                random.random()
            ),
        )
        tables = []

        for group_id, group in sorted_groups:
            placed = False
            group_size = len(group)

            for table in tables:
                if (table['size'] + group_size <= self.table_size and
                        not any(existing_gid in self.group_conflicts[group_id]
                                for existing_gid in table['group_ids'])):
                    table['group_ids'].append(group_id)
                    table['size'] += group_size
                    placed = True
                    break

            if not placed:
                if len(tables) >= self.num_tables:
                    raise ValueError("Not enough tables")
                tables.append({
                    'group_ids': [group_id],
                    'size': group_size
                })

        table_assignments = []
        for table in tables:
            guests = []
            for gid in table['group_ids']:
                guests.extend(self.must_groups[gid])
            table_assignments.append(guests)
        return table_assignments

    def _arrange_seats(self, guests):
        n = len(guests)
        if n < 2:
            return guests.copy()

        must_pairs = defaultdict(set)
        prefer_pairs = defaultdict(set)
        avoid_pairs = defaultdict(set)

        for a, b in combinations(guests, 2):
            pair = frozenset({a, b})
            constr = self.constraints.get(pair, {})
            if constr.get('must'):
                must_pairs[a].add(b)
                must_pairs[b].add(a)
            if constr.get('prefer'):
                prefer_pairs[a].add(b)
                prefer_pairs[b].add(a)
            if constr.get('prefer_apart') or constr.get('must_not'):
                avoid_pairs[a].add(b)
                avoid_pairs[b].add(a)

        arranged = []
        unplaced = set(guests)

        while unplaced:
            found = False
            for guest in list(unplaced):
                if must_pairs[guest]:
                    partner = must_pairs[guest].pop()
                    if partner in unplaced:
                        arranged.extend([guest, partner])
                        unplaced.remove(guest)
                        unplaced.remove(partner)
                        found = True
                        break
            if not found:
                break

        while unplaced:
            best_score = -1
            best_pos = -1
            best_guest = None

            for guest in unplaced:
                for pos in range(len(arranged) + 1):
                    left = arranged[pos - 1] if pos > 0 else None
                    right = arranged[pos] if pos < len(arranged) else None

                    score = 0
                    if left and left in prefer_pairs[guest]:
                        score += 2
                    if right and right in prefer_pairs[guest]:
                        score += 2
                    if left and left in avoid_pairs[guest]:
                        score -= 3
                    if right and right in avoid_pairs[guest]:
                        score -= 3

                    if score > best_score:
                        best_score = score
                        best_pos = pos
                        best_guest = guest

            if best_guest:
                arranged.insert(best_pos, best_guest)
                unplaced.remove(best_guest)
            else:
                arranged.append(unplaced.pop())

        for i in range(n):
            a, b = arranged[i], arranged[(i + 1) % n]
            if b in avoid_pairs[a]:
                for j in range(n):
                    if j == i or j == (i + 1) % n:
                        continue
                    c = arranged[j]
                    if c not in avoid_pairs[a] and c not in avoid_pairs[b]:
                        arranged[i], arranged[j] = arranged[j], arranged[i]
                        break

        return arranged

    def generate_seating(self):
        try:
            self._form_must_groups()
            self._build_group_conflicts()
            tables = self._assign_groups_to_tables()
            return {
                'tables': [self._arrange_seats(table) for table in tables],
                'message': 'Success'
            }
        except ValueError as e:
            return {'tables': [], 'message': str(e)}

    def validate(self, seating):
        errors = []
        guest_table = {}
        for tid, table in enumerate(seating):
            for guest in table:
                guest_table[guest] = tid

        for pair, constr in self.constraints.items():
            a, b = tuple(pair)
            if constr['must'] and guest_table.get(a) != guest_table.get(b):
                errors.append(f"{a} & {b} must be together")
            if constr['must_not'] and guest_table.get(a) == guest_table.get(b):
                errors.append(f"{a} & {b} must be separated")

        for table in seating:
            n = len(table)
            for i in range(n):
                a, b = table[i], table[(i + 1) % n]
                if self.constraints[frozenset({a, b})]['prefer_apart']:
                    errors.append(f"{a} & {b} are adjacent but should be apart")
        return errors


def find_optimal_configuration(num_people, people, constraints, min_size=5, max_size=10):
    if min_size > max_size:
        return {
            'tables': [],
            'message': 'Minimum table size cannot be greater than maximum table size'
        }, None, None, None

    best_result = None
    best_score = float('-inf')
    best_table_size = None
    best_num_tables = None

    for table_size in range(min_size, max_size + 1):
        min_tables = (num_people + table_size - 1) // table_size

        for num_tables in range(min_tables, min_tables + 3):
            try:
                generator = SeatingGenerator(
                    guests=people,
                    table_size=table_size,
                    num_tables=num_tables,
                    constraints=constraints
                )
                result = generator.generate_seating()
                if not result['tables']:
                    continue

                if not all(min_size <= len(table) <= table_size for table in result['tables']):
                    continue

                score = calculate_arrangement_score(result['tables'], generator.constraints)
                if score > best_score:
                    best_score = score
                    best_result = result
                    best_table_size = table_size
                    best_num_tables = num_tables
            except Exception as e:
                continue

    if best_result is None:
        return {
            'tables': [],
            'message': f'Could not find valid arrangement with tables between {min_size} and {max_size} people'
        }, None, None, None

    return best_result, best_table_size, best_num_tables, best_score


def calculate_arrangement_score(tables, constraints):
    score = 0
    table_sizes = [len(table) for table in tables]
    size_variance = sum((size - sum(table_sizes) / len(table_sizes)) ** 2 for size in table_sizes)
    score -= size_variance * 2

    for table in tables:
        for i, person1 in enumerate(table):
            for j, person2 in enumerate(table):
                if i < j:
                    pair = frozenset({person1, person2})
                    if constraints.get(pair, {}).get('prefer', False):
                        score += 15
                    if constraints.get(pair, {}).get('prefer_apart', False):
                        score -= 20
    return score


def print_detailed_report(people, constraints, tables, table_size, num_tables):
    print("\n=== SEATING ARRANGEMENT DETAILS ===")
    print(f"\nConfiguration:")
    print(f"- Total guests: {len(people)}")
    print(f"- Table size: {table_size}")
    print(f"- Number of tables: {num_tables}")

    print("\n=== TABLE ASSIGNMENTS ===")
    for i, table in enumerate(tables, 1):
        print(f"\nTable {i} ({len(table)} people):")
        print("  " + "\n  ".join([", ".join(table[i:i + 5]) for i in range(0, len(table), 5)]))

        print("\n  Notable relationships:")
        notable = False
        for a, b in combinations(table, 2):
            pair = frozenset({a, b})
            constr = constraints.get(pair, {})
            relations = []
            if constr.get('must'):
                relations.append("MUST sit together")
            if constr.get('must_not'):
                relations.append("MUST NOT sit together")
            if constr.get('prefer'):
                relations.append("Preferred neighbors")
            if constr.get('prefer_apart'):
                relations.append("Prefer apart")
            if relations:
                print(f"  {a} & {b}: {', '.join(relations)}")
                notable = True
        if not notable:
            print("  No special relationships")


def visualize_seating(seating):
    num_tables = len(seating)
    colors = ['#FFE4E1', '#E0FFFF', '#F0FFF0', '#FFF0F5', '#F5F5DC']

    cols = int(np.ceil(np.sqrt(num_tables)))
    rows = int(np.ceil(num_tables / cols))

    fig_width = max(12, cols * 6)
    fig_height = max(8, rows * 5)
    plt.figure(figsize=(fig_width, fig_height))

    for i, table in enumerate(seating, 1):
        ax = plt.subplot(rows, cols, i, aspect='equal')
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.5, 1.5)
        ax.axis('off')

        table_circle = plt.Circle((0, 0), 1.0, color=colors[i % len(colors)], alpha=0.3)
        ax.add_artist(table_circle)

        plt.text(0, 0, f"Table {i}",
                 ha='center', va='center',
                 fontsize=16, weight='bold',
                 color='#333333')

        n = len(table)
        angle_step = 2 * np.pi / n
        for idx, name in enumerate(table):
            angle = idx * angle_step - np.pi / 2
            x = np.cos(angle) * 1.2
            y = np.sin(angle) * 1.2

            max_name_len = max(len(n) for n in table)
            if max_name_len > 15:
                font_size = 10
            elif max_name_len > 10:
                font_size = 12
            else:
                font_size = 14 if n < 8 else 12

            rotation_angle = angle * 180 / np.pi
            if 90 < rotation_angle < 270:
                rotation_angle += 180

            plt.text(x, y, name,
                     ha='center', va='center',
                     rotation=rotation_angle,
                     fontsize=font_size,
                     rotation_mode='anchor')

    plt.tight_layout(pad=3.0, w_pad=4.0, h_pad=4.0)
    return plt.gcf()


def explore_arrangements(people, constraints, table_size, num_tables, max_attempts=100):
    seen = set()
    arrangements = []

    for _ in range(max_attempts):
        generator = SeatingGenerator(people, table_size, num_tables, constraints)
        result = generator.generate_seating()

        if result['tables']:
            errors = generator.validate(result['tables'])
            if not errors:
                normalized = []
                for table in result['tables']:
                    sorted_table = sorted(table)
                    normalized.append(tuple(sorted_table))
                normalized.sort(key=lambda x: x[0])
                arrangement_key = tuple(normalized)

                if arrangement_key not in seen:
                    seen.add(arrangement_key)
                    score = calculate_arrangement_score(result['tables'], generator.constraints)
                    arrangements.append((score, result['tables']))

    arrangements.sort(reverse=True, key=lambda x: x[0])
    return arrangements


def get_real_data():
    print("\n=== GUEST LIST ===")
    guests = []
    while True:
        guest_input = input("Enter guest names (comma-separated): ").strip()
        if guest_input:
            guests = [name.strip() for name in guest_input.split(',')]
            guests = [' '.join([part.capitalize() for part in name.split()]) for name in guests]
            guests = list(dict.fromkeys(guests))
            if len(guests) < 2:
                print("Please enter at least 2 guests")
                continue
            break
        print("Please enter at least one guest")

    print("\n=== RELATIONSHIP CONSTRAINTS ===")
    print("Enter relationships one at a time. Format:")
    print("- 'A must B' for people who MUST sit in the same table")
    print("- 'A cannot B' for people who MUST NOT be in the same table")
    print("- 'A prefer B' for people who would like to be in the same table")
    print("- 'A avoid B' for people who would like to be in different tables")
    print("- Type 'done' when finished\n")

    valid_relations = {'must', 'cannot', 'prefer', 'avoid'}
    constraints = []
    while True:
        rel_input = input("Enter relationship (or 'done'): ").strip()
        if rel_input.lower() == 'done':
            break

        tokens = rel_input.split()
        found = False
        for i, token in enumerate(tokens):
            if token.lower() in valid_relations:
                if i == 0 or i == len(tokens) - 1:
                    print("Error: Relation cannot be at the start or end")
                    found = True
                    break
                name1 = ' '.join(tokens[:i])
                name1 = ' '.join([part.capitalize() for part in name1.split()])
                name2 = ' '.join(tokens[i + 1:])
                name2 = ' '.join([part.capitalize() for part in name2.split()])
                rel_type = token.lower()

                if name1 not in guests:
                    print(f"Error: {name1} is not in the guest list")
                    found = True
                    break
                if name2 not in guests:
                    print(f"Error: {name2} is not in the guest list")
                    found = True
                    break

                constraint_map = {
                    'must': 'must',
                    'cannot': 'must_not',
                    'prefer': 'prefer',
                    'avoid': 'prefer_apart'
                }
                constraints.append((name1, name2, constraint_map[rel_type]))
                found = True
                break
        if not found:
            print("Invalid format. Use: [Name1] [relation] [Name2]")

    return guests, constraints


def generate_test_data(num_people):
    people = []
    while len(people) < num_people:
        name = names.get_full_name()
        if name not in people:
            people.append(name)

    constraints = []
    families = []
    remaining_people = people.copy()

    while remaining_people:
        family_size = min(random.randint(2, 4), len(remaining_people))
        family = random.sample(remaining_people, family_size)
        families.append(family)
        for person in family:
            remaining_people.remove(person)

    for family in families:
        for a, b in combinations(family, 2):
            constraints.append((a, b, 'must'))

    num_must_not = max(1, num_people // 15)
    for _ in range(num_must_not):
        if len(families) >= 2:
            family1, family2 = random.sample(families, 2)
            a = random.choice(family1)
            b = random.choice(family2)
            constraints.append((a, b, 'must_not'))

    existing_pairs = set()
    for person in people:
        family = next(f for f in families if person in f)
        potential_friends = [p for p in people if p not in family and p != person]
        num_prefer = random.randint(0, min(3, len(potential_friends)))
        prefer = random.sample(potential_friends, num_prefer)
        for p in prefer:
            pair = frozenset({person, p})
            if pair not in existing_pairs:
                constraints.append((person, p, 'prefer'))
                existing_pairs.add(pair)

        potential_avoid = [p for p in people if p not in family and p != person]
        num_avoid = random.randint(0, min(2, len(potential_avoid)))
        avoid = random.sample(potential_avoid, num_avoid)
        for p in avoid:
            pair = frozenset({person, p})
            if pair not in existing_pairs:
                constraints.append((person, p, 'prefer_apart'))
                existing_pairs.add(pair)

    return people, constraints


def main():
    print("=== WEDDING SEATING ARRANGEMENT GENERATOR ===")

    if input("\nUse test data? (y/n): ").lower() == 'y':
        num_people = int(input("Enter number of test guests: "))
        people, constraints = generate_test_data(num_people)
    else:
        people, constraints = get_real_data()

    constraints_dict = defaultdict(
        lambda: {'must': False, 'must_not': False, 'prefer': False, 'prefer_apart': False})
    for a, b, constraint in constraints:
        pair = frozenset({a, b})
        constraints_dict[pair][constraint] = True

    print("\n=== TABLE CONFIGURATION ===")
    if input("Use automatic table size optimization? (y/n): ").lower() == 'y':
        min_size = int(input("Minimum table size (default 5): ") or 5)
        max_size = int(input("Maximum table size (default 10): ") or 10)
        result, table_size, num_tables, _ = find_optimal_configuration(
            len(people), people, constraints, min_size, max_size
        )
        if not result['tables']:
            print("\nFailed to create seating arrangement:", result['message'])
            return
        generator = SeatingGenerator(people, table_size, num_tables, constraints)
    else:
        table_size = int(input("Enter fixed table size: "))
        num_tables = (len(people) + table_size - 1) // table_size
        generator = SeatingGenerator(people, table_size, num_tables, constraints)
        result = generator.generate_seating()
        if not result['tables']:
            print("\nFailed to create seating arrangement:", result['message'])
            return

    print("\n=== GENERATING POSSIBLE ARRANGEMENTS ===")
    arrangements = explore_arrangements(people, constraints, table_size, num_tables)

    if not arrangements:
        print("\nNo valid arrangements found")
        return

    current_idx = 0
    total_arrangements = len(arrangements)

    while True:
        score, tables = arrangements[current_idx]
        print(f"\n=== Arrangement {current_idx + 1}/{total_arrangements}")
        print_detailed_report(people, constraints_dict, tables, table_size, num_tables)
        visualize_seating(tables)

        if current_idx < total_arrangements - 1:
            choice = input("\nView next arrangement? (y/n): ").lower()
            if choice == 'y':
                current_idx += 1
            else:
                break
        else:
            print("\nNo more arrangements available")
            break

    errors = generator.validate(result['tables'])
    if errors:
        print("\n=== VALIDATION ERRORS ===")
        for error in errors[:5]:
            print(f" - {error}")
        if len(errors) > 5:
            print(f"  ...and {len(errors) - 5} more errors")
    else:
        print("\n=== VALIDATION PASSED ===")


if __name__ == "__main__":
    main()

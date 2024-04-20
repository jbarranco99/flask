from flask import Flask, request, jsonify
import os

app = Flask(__name__)


def get_value(d, path):
    """Safely get a value from a nested dictionary using a list of keys."""
    for key in path:
        try:
            if isinstance(d, dict):
                d = d[key]
            else:
                d = d[int(key)]
        except (KeyError, TypeError, ValueError, IndexError):
            return None
    return d


def find_levels(data, target_values, current_path=None, results=None):
    """Recursively find and record levels of target values in a nested structure."""
    if current_path is None:
        current_path = []
    if results is None:
        results = set()
    if isinstance(data, dict):
        for key, value in data.items():
            if key in target_values:
                results.add(('Key', key, tuple(current_path)))  # Convert path to tuple
            find_levels(value, target_values, current_path + [key], results)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            if item in target_values:
                results.add(('Value', item, tuple(current_path + [str(index)])))  # Convert path to tuple
            find_levels(item, target_values, current_path + [str(index)], results)
    return list(results)


@app.route('/menuToFullTree', methods=['POST'])
def menuToFullTree():
    try:
        req_data = request.get_json()
        menu_items = req_data['queryMenu']

        # Initialize the categories dictionary
        categories = {"categories": {"categories": {}}}
        category_map = {
            "names": [],
            "subcategories": {}
        }

        # Iterate through the menu items and build the categories
        for item in menu_items:
            current_category = categories["categories"]["categories"]
            current_category_map = category_map
            for i in range(1, 6):
                category = item.get(f'category{i}')
                if category:
                    if category not in current_category:
                        current_category[category] = {}
                    current_category = current_category[category]
                    if category not in current_category_map["names"]:
                        current_category_map["names"].append(category)
                    if category not in current_category_map["subcategories"]:
                        current_category_map["subcategories"][category] = {
                            "names": [],
                            "subcategories": {}
                        }
                    current_category_map = current_category_map["subcategories"][category]
                else:
                    break

            if 'items' not in current_category:
                current_category['items'] = []

            menu_item = {
                'name': item['name'],
                'price': item['price'],
                'vegan': item['vegan'] == 'TRUE',
                'vegetarian': item['vegetarian'] == 'TRUE',
                'description': item['description'],
                'gluten_free': item['gluten_free'] == 'TRUE',
                'restaurant_id': item['restaurant_id']
            }
            current_category['items'].append(menu_item)

        response = {
            'fullMap': {
                'categories': categories["categories"],
                'categoryMap': category_map
            }
        }

        return jsonify(response)

    except (KeyError, TypeError):
        return jsonify({'error': 'Invalid input data'}), 400


@app.route('/')
def index():
    return jsonify({"Choo Choo": "Welcome to your Flask app 🚅"})


@app.route('/test', methods=['POST'])
def process_data():
    # Parse JSON from the request
    req_data = request.get_json()
    data = req_data['data']
    gameStage = req_data['gameStage']
    pickedCats = req_data['pickedCats']
    pendingcat1 = req_data['pendingcat1']
    pendingCategories = req_data['pendingCategories']
    userInput = req_data['userInput']
    selection_paths = req_data['selection_paths']
    selection_paths = string_paths_to_lists(selection_paths, delimiter='/')
    game_started = req_data['game_started']
    menu_data = req_data.get('menu', {})  # The complete menu data
    answers = []
    filtered_items = []  # To store the final filtered items

    if pendingcat1 == [] and game_started == 0:
        pendingcat1 = [cat for cat in pickedCats if cat in data['names']]
        game_started = 1

    if len(pendingcat1) >= len(pendingCategories):
        answers = get_value(data, ['subcategories', pendingcat1[0], 'names'])

        selection_path = ['subcategories', pendingcat1[0]]
        selection_paths.append(selection_path)
        
        pendingcat1.pop(0)
        pendingCategories.extend(answers)
        


    else:
        results = find_levels(data, userInput)
        filtered_results = [result for result in results if result[0] == 'Key']

        unique_answers = set()
        for result in filtered_results:
            _, value, path = result
            full_path = list(path) + [value, 'names']
            current_answers = get_value(data, full_path)
            if current_answers is not None:
                if isinstance(current_answers, list):
                    unique_answers.update(current_answers)
                else:
                    unique_answers.add(current_answers)
                # Update selection_paths with the current path
                selection_paths.append(full_path[:-1])  # Exclude 'names' from the path

        answers.extend(unique_answers)

    # Combine allowed values: pendingcat1, user_input, and answers
    allowed_values = set(pendingcat1 + answers)

    # Update pending_categories to include only allowed values, and add new answers to the start
    pending_categories = [item for item in answers + pendingcat1]

    if len(pendingcat1) == len(pending_categories):
        gameStage = "dishPicker"
        terminal_paths = filter_complete_paths(selection_paths)
        # Traverse each path to find and accumulate the corresponding items
        # Assuming 'menu_data' is your complete menu structure
        # and 'terminal_paths' are the paths you've determined to traverse:
        for path in terminal_paths:
            current_section = menu_data['categories']  # Starting point for traversal
            for category in path:
                if category in current_section:
                    current_section = current_section[category]
                else:
                    current_section = None
                    break
            items = find_items(current_section) if current_section else None
            if items:
                filtered_items.extend(items)

    selection_paths_strings = paths_to_string(selection_paths, delimiter='/')

    return jsonify({
        "gameStage": gameStage,
        "answers": answers,
        "pendingcat1": pendingcat1,
        "pending_categories": pending_categories,
        "selection_paths": selection_paths_strings,
        "game_started": game_started,
        "filtered_items": filtered_items
    })


def filter_complete_paths(paths):
    simplified_paths = [[item for item in path if item.lower() != "subcategories"] for path in paths]
    complete_paths = filter_paths_with_all_ancestors(simplified_paths)
    terminal_paths = filter_for_terminal_paths(complete_paths)

    return terminal_paths


def filter_paths_with_all_ancestors(simplified_paths):
    paths_as_tuples_set = set(tuple(path) for path in simplified_paths)
    complete_paths_tuples = [path for path in paths_as_tuples_set if
                             immediate_ancestor_present(path, paths_as_tuples_set)]
    complete_paths_lists = [list(path) for path in complete_paths_tuples]
    return ensure_base_paths(complete_paths_lists)


def immediate_ancestor_present(path, all_paths_set):
    if len(path) == 1:
        return True
    immediate_ancestor = path[:-1]
    return tuple(immediate_ancestor) in all_paths_set


def ensure_base_paths(complete_paths_lists):
    for path in complete_paths_lists:
        if len(path) > 1:
            base_path = path[:2]
            if base_path not in complete_paths_lists:
                complete_paths_lists.append(base_path)
    return complete_paths_lists


def filter_for_terminal_paths(paths):
    terminal_paths = [path for path in paths if not any(is_prefix(path, other) for other in paths if path != other)]
    return terminal_paths


def is_prefix(path, other_path):
    if len(path) >= len(other_path):
        return False
    return all(path[i] == other_path[i] for i in range(len(path)))


def convert_selection_paths(input_paths):
    converted_paths = []
    for path_str in input_paths:
        # Remove the brackets at the beginning and the end, then split by ', '
        path_elements = path_str[1:-1].split(", ")
        # Trim the extra quotes from each element and keep the structure
        clean_elements = [element.strip("'") for element in path_elements]
        converted_paths.append(clean_elements)
    return converted_paths


def string_paths_to_lists(string_paths, delimiter='/'):
    """
    Convert a list of string paths to a list of lists of keys.
    """
    return [path.split(delimiter) for path in string_paths]


def paths_to_string(paths, delimiter='/'):
    """
    Convert each path in paths to a string using the given delimiter.
    """
    return [delimiter.join(path) for path in paths]


def find_items(current_section):
    if 'items' in current_section:
        return current_section['items']
    for key, subsection in current_section.items():
        if isinstance(subsection, dict):
            items = find_items(subsection)
            if items:
                return items
    return None


VERSION = "1.0.0"

@app.route('/scoringSystem', methods=['POST'])
def scoringSystem():
    data = request.get_json()
    full_menu = data.get('fullMenu', [])
    user_input = data.get('userInput', [])
    all_questions = data.get('allQuestions', [])
    dish_features = data.get('dishFeatures', [])
    question_choices = data.get('questionChoices', [])
    
    filtered_menu, _ = filter_dishes(full_menu, user_input, all_questions, question_choices, dish_features)
    scored_dishes = calculate_scores(filtered_menu, user_input, dish_features, question_choices, all_questions)
    
    response = {
        "dishes": scored_dishes
    }
    
    return jsonify(response)

def filter_dishes(full_menu, user_input, all_questions, question_choices, dish_features):
    filtered_menu = []
    debug_info = []

    # Extract the user's dietary restrictions
    dietary_restrictions = user_input[0]['answer']

    # Find the question ID for the dietary restrictions question
    dietary_question = next((q for q in all_questions if q['type'] == 'hard'), None)
    dietary_question_id = dietary_question['id'] if dietary_question else None

    # Filter dishes based on dietary restrictions
    for dish in full_menu:
        dish_id = dish['id']
        dish_debug_info = {
            "dish_id": dish_id,
            "dish_name": dish["name"],
            "dietary_restrictions": dietary_restrictions,
            "dish_features": [],
            "satisfies_restrictions": True,
            "restriction_checks": []
        }

        # Get the dish features
        dish_features_filtered = [feature for feature in dish_features if feature['dish_id'] == dish_id]
        dish_debug_info["dish_features"] = dish_features_filtered

        # Check if the dish satisfies all dietary restrictions
        for restriction in dietary_restrictions:
            restriction_feature = next((feature for feature in dish_features_filtered if feature['feature'].lower() == restriction.lower()), None)

            if restriction_feature:
                dish_debug_info["restriction_checks"].append({
                    "restriction": restriction,
                    "feature_value": restriction_feature['value']
                })

                if restriction_feature['value'].lower() != 'true':
                    dish_debug_info["satisfies_restrictions"] = False
            else:
                dish_debug_info["restriction_checks"].append({
                    "restriction": restriction,
                    "feature_value": "NOT FOUND"
                })
                dish_debug_info["satisfies_restrictions"] = False

        debug_info.append(dish_debug_info)

        if dish_debug_info["satisfies_restrictions"]:
            filtered_menu.append(dish)

    return filtered_menu, debug_info

def calculate_scores(filtered_menu, user_input, dish_features, question_choices, all_questions):
    scored_dishes = []
    debug_info = []

    # Extract only the 'soft' questions from user_input
    soft_questions_input = [q for q in user_input if q['question_type'] == 'soft']

    for dish in filtered_menu:
        dish_id = dish['id']
        dish_score = 0
        dish_debug = {
            'dish_id': dish_id,
            'dish_name': dish['name'],
            'features': []
        }

        # Process each 'soft' question and calculate scores
        for soft_question in soft_questions_input:
            question_id = soft_question['question_id']
            user_answer_values = [int(a) for a in soft_question['answer']]
            dish_feature_values = []

            # Get choices linked to this particular 'soft' question
            choices_for_question = [choice for choice in question_choices if choice['question_id'] == question_id]

            # Iterate over these choices and match them with dish features
            for choice in choices_for_question:
                feature_id = choice['feature_id']
                feature = next((f for f in dish_features if f['id'] == feature_id and f['dish_id'] == dish_id), None)

                if feature:
                    converted_value = int(feature['value'])
                    dish_feature_values.append(converted_value)
                    dish_debug['features'].append({
                        'feature_id': feature_id,
                        'feature_name': choice['text'],
                        'feature_value': feature['value']
                    })
                else:
                    dish_feature_values.append(0)  # No matching feature found, so append 0
                    dish_debug['features'].append({
                        'feature_id': feature_id,
                        'feature_name': choice['text'],
                        'feature_value': 'NOT FOUND'
                    })

            # Ensure both lists have the same length for comparison
            max_length = max(len(user_answer_values), len(dish_feature_values))
            user_answer_values.extend([0] * (max_length - len(user_answer_values)))
            dish_feature_values.extend([0] * (max_length - len(dish_feature_values)))

            # Calculate score by summing differences
            dish_score += sum(abs(uv - fv) for uv, fv in zip(user_answer_values, dish_feature_values))

        scored_dish = dish.copy()
        scored_dish['score'] = dish_score
        scored_dishes.append(scored_dish)
        debug_info.append(dish_debug)

    response = {
        'dishes': scored_dishes,
        'debug_info': debug_info
    }

    return response



def convert_value(value):
    try:
        if value.lower() == 'true':
            return 1
        elif value.lower() == 'false':
            return 0
        return int(value)
    except ValueError:
        return 0  # Default to 0 if conversion fails


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=5000)

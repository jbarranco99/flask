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
def menu_to_full_tree():
    try:
        req_data = request.get_json()
        menu_items = req_data['queryMenu']
        
        # Initialize the categories dictionary
        categories = {"categories": {}}
        category_map = {
            "names": [],
            "subcategories": {}
        }

        # Iterate through the menu items and build the categories
        for item in menu_items:
            current_category = categories["categories"]
            current_category_map = category_map
            
            for i in range(1, 6):
                category = item.get(f'category{i}')
                if category:
                    if category not in current_category:
                        current_category[category] = {'items': []}
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

            # Add menu item details
            menu_item = {
                'name': item['name'],
                'price': item['price'],
                'description': item['description'],
                'restaurant_id': item['restaurant_id'],
                'score': item['score'],
                'picture': item['picture'],
                'recommend': item['recommend'],
                'id': item['id'],
                'category1': item.get('category1', ''),
                'category2': item.get('category2', ''),
                'category3': item.get('category3', ''),
                'category4': item.get('category4', ''),
                'category5': item.get('category5', '')
            }
            current_category['items'].append(menu_item)

        # Build the response
        response = {
            'fullMap': {
                'categories': categories["categories"],
                'categoryMap': category_map
            }
        }
        return jsonify(response)
    except (KeyError, TypeError) as e:
        # Return error response if there's an issue with input data
        return jsonify({'error': f'Invalid input data: {str(e)}'}), 400

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
                             all_ancestors_present(path, paths_as_tuples_set)]
    complete_paths_lists = [list(path) for path in complete_paths_tuples]
    return complete_paths_lists

def all_ancestors_present(path, all_paths_set):
    for i in range(1, len(path)):
        ancestor = tuple(path[:i])
        if ancestor not in all_paths_set:
            return False
    return True

def immediate_ancestor_present(path, all_paths_set):
    if len(path) == 1:
        return True
    immediate_ancestor = path[:-1]
    return tuple(immediate_ancestor) in all_paths_set

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


def calculate_scores(filtered_menu, user_input, dish_features, question_choices, all_questions):
    scored_dishes = []
    debug_info = []

    # Extract only the 'soft' questions from user_input
    soft_questions_input = [q for q in user_input if q['question_type'] == 'soft']

    for dish in filtered_menu:
        dish_id = dish['id']
        dish_score = 0
        exclude_dish = False  # Flag to determine if the dish should be excluded
        dish_debug = {
            'dish_id': dish_id,
            'dish_name': dish['name'],
            'features': [],
            'processing_steps': []  # To store detailed step-by-step processing info
        }

        # Process each 'soft' question and calculate scores
        for soft_question in soft_questions_input:
            question_id = soft_question['question_id']
            user_answers = soft_question['answer']
            user_answer_dict = {}
            for ans in user_answers:
                feature_name, value = ans.split(": ")
                user_answer_dict[feature_name.strip().lower()] = int(value.strip())

            dish_debug['processing_steps'].append({
                'step': 'Parse user answers',
                'question_id': question_id,
                'parsed_answers': user_answer_dict
            })

            # Get features linked to this particular 'soft' question and filter by current dish
            dish_features_list = [f for f in dish_features if f['dish_id'] == dish_id]

            # Iterate over these filtered features and match them with user answers
            for feature in dish_features_list:
                feature_text = feature['feature'].lower()
                if feature_text in user_answer_dict:
                    feature_value = convert_value(feature['value']) if feature['value'] is not None else None

                    if feature_value is None:
                        exclude_dish = True  # Set the flag to exclude this dish if feature is missing
                        break  # No need to process further features for this dish

                    user_value = user_answer_dict[feature_text]
                    score_difference = abs(user_value - feature_value)
                    if score_difference > 1:
                        exclude_dish = True  # Set the flag to exclude this dish
                        break  # No need to process further features for this dish

                    dish_score += score_difference
                    dish_debug['features'].append({
                        'feature_id': feature['id'],
                        'feature_name': feature['feature'],
                        'user_value': user_value,
                        'feature_value': feature_value,
                        'score_contribution': score_difference
                    })

            if exclude_dish:
                break  # Stop processing further soft questions for this dish

        if not exclude_dish:
            scored_dish = dish.copy()
            scored_dish['score'] = dish_score
            scored_dishes.append(scored_dish)
            debug_info.append(dish_debug)

    # Sort the dishes by score in descending order
    scored_dishes.sort(key=lambda x: x['score'], reverse=True)
    response = {
        'dishes': {'dishes': scored_dishes},
        'debug_info': debug_info
    }
    return response

def convert_value(value):
    if value is None:
        return None
    if value.lower() == 'true':
        return 1
    elif value.lower() == 'false':
        return 0
    try:
        return int(value)
    except ValueError:
        return 0  # Default to 0 if conversion fails

        

@app.route('/recommenderSystem', methods=['POST'])
def recommenderSystem():
    data = request.get_json()
    scored_dishes = data['scoredDishes']
    historic_shortlist = data['historicShorlist']
    swiped_left = data['swipedLeft']
    
    # Get all the dishes from scoredDishes where recommend = true
    recommended_dishes = [dish for dish in scored_dishes if dish['recommend']]
    
    # Create sets of dish IDs for efficient lookup
    historic_shortlist_ids = set(dish['id'] for dish in historic_shortlist)
    swiped_left_ids = set(dish['id'] for dish in swiped_left)
    
    # Filter out dishes that are in either swipedLeft or historicShortlist
    filtered_dishes = [
        dish for dish in recommended_dishes
        if dish['id'] not in historic_shortlist_ids and dish['id'] not in swiped_left_ids
    ]
    
    return jsonify(filtered_dishes)

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=5000)

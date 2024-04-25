from flask import Flask, request, jsonify
import os
app = Flask(__name__)

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
                'restaurant_id': item['restaurant_id'],
                'score': item['score']
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
        filtered_paths = filter_complete_paths(selection_paths)
        # Traverse each path to find and accumulate the corresponding items
        for path in filtered_paths:
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
    selection_paths_strings = paths_to_string(filtered_paths, delimiter='/')
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
    """
    Filter paths to ensure each path has a valid predecessor path.
    """
    valid_paths = []
    paths_as_tuples = [tuple(path) for path in paths]
    path_set = set(paths_as_tuples)

    for path in paths_as_tuples:
        if is_path_valid(path, path_set):
            valid_paths.append(list(path))
    
    return valid_paths

def is_path_valid(path, path_set):
    """
    Check if every prefix of the path is in the set of paths, ensuring path integrity.
    """
    for depth in range(1, len(path)):
        if tuple(path[:depth]) not in path_set:
            return False
    return True

def find_items(current_section):
    """
    Find items in the given section of the menu.
    """
    if 'items' in current_section:
        return current_section['items']
    return None

def get_value(data, path):
    """
    Safely get a value from a nested dictionary using a list of keys.
    """
    for key in path:
        try:
            if isinstance(data, dict):
                data = data[key]
            else:
                data = data[int(key)]
        except (KeyError, TypeError, ValueError, IndexError):
            return None
    return data

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

def find_levels(data, target_values, current_path=None, results=None):
    """
    Recursively find and record levels of target values in a nested structure.
    """
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

if __name__ == '__main__':
    app.run(debug=True)

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
    # Find all hard questions
    hard_questions = [q for q in all_questions if q['type'] == 'hard']
    # Filter dishes based on all hard question restrictions
    for dish in full_menu:
        dish_id = dish['id']
        dish_debug_info = {
            "dish_id": dish_id,
            "dish_name": dish["name"],
            "dish_features": [],
            "satisfies_all_restrictions": True,
            "restriction_checks": []
        }
        # Get the dish features
        dish_features_filtered = [feature for feature in dish_features if feature['dish_id'] == dish_id]
        dish_debug_info["dish_features"] = dish_features_filtered
        # Check if the dish satisfies all applicable restrictions from user inputs
        for question in hard_questions:
            # Find the user input for this question
            user_answers = next((input for input in user_input if input['question_id'] == question['id']), None)
            if not user_answers:
                continue  # No user input for this question
            for answer in user_answers['answer']:
                # Normalize the answer to match feature names exactly or assume it's boolean 'TRUE'
                restriction_feature = next((feature for feature in dish_features_filtered if feature['feature'].lower() == answer.lower()), None)
                if restriction_feature:
                    dish_debug_info["restriction_checks"].append({
                        "restriction": answer,
                        "feature_value": restriction_feature['value']
                    })
                    if restriction_feature['value'].lower() != 'true':
                        dish_debug_info["satisfies_all_restrictions"] = False
                else:
                    dish_debug_info["restriction_checks"].append({
                        "restriction": answer,
                        "feature_value": "NOT FOUND"
                    })
                    dish_debug_info["satisfies_all_restrictions"] = False
        debug_info.append(dish_debug_info)
        if dish_debug_info["satisfies_all_restrictions"]:
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
            'features': [],
            'processing_steps': []  # To store detailed step-by-step processing info
        }
        # Process each 'soft' question and calculate scores
        for soft_question in soft_questions_input:
            question_id = soft_question['question_id']
            user_answers = soft_question['answer']
            # Parse user answers into feature names and their values
            user_answer_dict = {}
            for ans in user_answers:
                feature_name, value = ans.split(": ")
                user_answer_dict[feature_name.strip().lower()] = int(value.strip())
            dish_debug['processing_steps'].append({
                'step': 'Parse user answers',
                'question_id': question_id,
                'parsed_answers': user_answer_dict
            })
            # Get choices linked to this particular 'soft' question and filter by current dish
            dish_features_list = [f for f in dish_features if f['dish_id'] == dish_id]
            # Iterate over these filtered features and match them with user answers
            for feature in dish_features_list:
                feature_text = feature['feature'].lower()
                if feature_text in user_answer_dict:
                    user_value = user_answer_dict[feature_text]
                    try:
                        feature_value = int(feature['value'])
                    except ValueError:
                        feature_value = 1 if feature['value'].upper() == 'TRUE' else 0
                    score_difference = abs(user_value - feature_value)
                    dish_score += score_difference
                    dish_debug['features'].append({
                        'feature_id': feature['id'],
                        'feature_name': feature['feature'],
                        'user_value': user_value,
                        'feature_value': feature['value'],
                        'score_contribution': score_difference
                    })
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

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
        results = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key in target_values:
                results.append(('Key', key, current_path))
            find_levels(value, target_values, current_path + [key], results)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            if item in target_values:
                results.append(('Value', item, current_path + [str(index)]))
            find_levels(item, target_values, current_path + [str(index)], results)
    return results
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
    game_started = req_data['game_started']
    answers = []

    if pendingcat1 == [] and game_started == 0:
        pendingcat1 = [cat for cat in pickedCats if cat in data['names']]
        game_started = 1
        
    if len(pendingcat1) >= len(pendingCategories):
        answers = get_value(data, ['subcategories', pendingcat1[0], 'names'])
        pendingcat1.pop(0)
        pendingCategories.extend(answers)
    else:
        results = find_levels(data, userInput)
        filtered_results = [result for result in results if result[0] == 'Key']

        for result in filtered_results:
            _, value, path = result
            full_path = path + [value, 'names']
            current_answers = get_value(data, full_path)
            if current_answers is not None:
                if isinstance(current_answers, list):
                    answers.extend(current_answers)
                else:
                    answers.append(current_answers)
                # Update selection_paths with the current path
                selection_paths.append(full_path[:-1])  # Exclude 'names' from the path

    # Combine allowed values: pendingcat1, user_input, and answers
    allowed_values = set(pendingcat1 + answers)

    # Update pending_categories to include only allowed values, and add new answers to the start
    pending_categories = [item for item in answers + pendingcat1]

    if len(pendingcat1) == len(pending_categories):
        gameStage = "dishPicker"

    return jsonify({
        "gameStage": gameStage,
        "answers": answers,
        "pendingcat1": pendingcat1,
        "pending_categories": pending_categories,
        "selection_paths": selection_paths,
        "game_started": game_started
    })

@app.route('/filterPaths', methods=['POST'])
def filter_paths():
    # Parse the request data for paths
    req_data = request.get_json()
    paths = req_data.get('paths', [])  # List of paths

    # Process paths to filter them
    largest_paths = filter_largest_paths(paths)
    complete_paths = filter_for_completeness(largest_paths, paths)

    # Return the filtered paths
    return jsonify({"filteredPaths": complete_paths})

def filter_largest_paths(paths):
    """Keep only the largest paths within each category."""
    paths.sort(key=len, reverse=True)  # Sort paths by length, longest first
    filtered_paths = []
    for path in paths:
        if not any(path[:len(fp)] == fp for fp in filtered_paths):
            filtered_paths.append(path)
    return filtered_paths

def filter_for_completeness(filtered_paths, original_paths):
    """Remove paths that are considered incomplete based on the absence of their necessary ancestor paths."""
    complete_paths = []
    for path in filtered_paths:
        if is_path_complete(path, original_paths):
            complete_paths.append(path)
    return complete_paths

def is_path_complete(path, paths):
    """Check if all necessary ancestor paths for a given path exist."""
    # Convert all paths to tuples for content-based comparison
    paths_as_tuples = [tuple(p) for p in paths]
    # Generate all ancestor paths for the given path
    ancestor_paths = [tuple(path[:i]) for i in range(1, len(path))]
    # Check if each ancestor path exists in the list of paths (using tuples for comparison)
    for ancestor in ancestor_paths:
        if ancestor not in paths_as_tuples:
            return False  # An ancestor path is missing, so the path is incomplete
    return True  # All ancestor paths exist, so the path is complete



if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=5000)

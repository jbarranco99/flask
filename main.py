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
    answers = []

    if pendingcat1 == [] and selection_paths == []:
        pendingcat1 = [cat for cat in pickedCats if cat in data['names']]

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
                latest_path = path

                # Reset selection_paths to only include the latest_path, ensuring it's not duplicated
        if latest_path is not None:
            selection_paths = [latest_path]  # Here we set selection_paths to only contain the latest path

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
        "selection_paths": selection_paths
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=5000)

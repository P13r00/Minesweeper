import json
from random import shuffle
from datetime import datetime
import sweeperlib


game = {
    "field": [],
    "revealed": set(),
    "flags": set(),
    "game_won": False,
    "complexity": 0,
    "move_count": 0,
    "correct_flags": 0 # only updated for losses
}

field_values = {}

database = {}


def load_database():
    """
    loads database, creates one if non existant
    """
    try:
        with open("minesweeper_stats.json", "r") as file:
            content = file.read().strip()
            if content:
                database = json.loads(content)
            else:
                raise ValueError("Empty file")
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        # If file not found or empty, create default database
        database = {
            "total_games": 0,
            "total_play_time": 0,  # in seconds
            "best_game": None,
            "game_history": []
        }

    with open("minesweeper_stats.json", "w") as file:
        json.dump(database, file, indent=4)

    return database

def create_field(width, height, num_mines):
    """
    creates a random playing field
    """
    # empty tiles
    field = []
    for _ in range(height):
        row = []
        for _ in range(width):
            row.append('0')
        field.append(row)
    
    # mine placing
    all_positions = []
    for row in range(height):
        for col in range(width):
            all_positions.append((row, col))
    shuffle(all_positions)
    for i in range(num_mines):
        row, col = all_positions[i]
        field[row][col] = "x"
    
    # number placing
    for row in range(height):
        for col in range(width):
            if field[row][col] == "x":
                continue
            
            # ninjas function
            count = 0
            for r in [row - 1, row, row + 1]:
                for c in [col - 1, col, col + 1]:
                    if r < 0 or r >= height or c < 0 or c >= width:
                        continue
                    if field[r][c] == "x":
                        count += 1
            field[row][col] = str(count)

    return field

def draw_field():
    """
    A handler function that draws a field represented by a two-dimensional list
    into a game window. This function is called whenever the game engine requests
    a screen update.
    """

    sweeperlib.clear_window()
    sweeperlib.draw_background()
    
    # prepare the sprite for each tile
    for y in range(field_values["height"]):
        for x in range(field_values["width"]):
            tile_position_x = x * 40
            tile_position_y = y * 40
            
            if (x, y) in game["revealed"]:
                sweeperlib.prepare_sprite(game["field"][y][x], tile_position_x, tile_position_y)
            else:
                sweeperlib.prepare_sprite(" ", tile_position_x, tile_position_y)

            if (x, y) in game["flags"]:
                sweeperlib.prepare_sprite("f", tile_position_x, tile_position_y)

    sweeperlib.draw_sprites()

def floodfill(start_row, start_col):
    """
    Marks previously unknown connected areas as safe, starting from the given
    x, y coordinates.
    """
    queue = [(start_row, start_col)]
    visited = set() # set to avoid duplicates

    while queue:
        row, col = queue.pop(0)
        if (row, col) in visited or\
            not (0 <= row < field_values["height"] and 0 <= col < field_values["width"]):
            continue
        visited.add((row, col))

        # reveal tile
        if (col, row) not in game["revealed"]:
            game["revealed"].add((col, row))

        # look at surrounding cells ONLY IF CELL IS EMPTY
        if game["field"][row][col] == "0":
            # ninjas function
            for r in [row - 1, row, row + 1]:
                for c in [col - 1, col, col + 1]:
                    if (r, c) != (row, col) and (c, r) not in game["revealed"]:
                        queue.append((r, c))

def handle_mouse(x, y, button, modifiers):
    """
    called when a mouse button is clicked inside the game window.
    Prints the position and clicked button of the mouse to the terminal.
    """
    row = y // 40
    col = x // 40

    if col in range(0, field_values["width"]) and row in range(0, field_values["height"]):
        if button == sweeperlib.MOUSE_LEFT:
            reveal_tile(row, col)
        elif button == sweeperlib.MOUSE_RIGHT:
            place_flag(row, col)

def game_end():
    """
    Called at the end of the game, prints the results, reveals all tiles and updates the stats
    """
    game["elapsed_time"] = round((datetime.now() - game["start_time"]).total_seconds())

    if game["game_won"]:
        print("You Win!")
        # Calculate score, 1/2 might not be the best value
        game["score"] = max(1, round(1000 * (game["complexity"] ** 0.1) / game["elapsed_time"]))
        game["final_result"] = "Victory"
    else:
        print("Game Over!")
        game["score"] = 0
        game["final_result"] = "Loss"
        for flag in game["flags"]:
            column, row = flag
            if game["field"][row][column] == 'x':
                game["correct_flags"] += 1

    # reveal all the tiles
    for y in range(field_values["height"]):
        for x in range(field_values["width"]):
            if (x, y) not in game["revealed"]:
                game["revealed"].add((x, y))

    game["flags"].clear()

    update_stats()

def reveal_tile(row, col):
    """
    reveals a tile in a position on the grid, 
    starts floodfill and checks for bombs and win condition.
    """
    if (col, row) in game["revealed"]:
        return

    game["revealed"].add((col, row))
    game["move_count"] += 1

    if game["field"][row][col] == "x":
        game_end()
        return
    if game["field"][row][col] == "0":
        floodfill(row, col)

    if len(game["revealed"]) == field_values["safe_tiles_number"]:
        game["game_won"] = True
        game_end()
        return

def place_flag(row, col):
    """
    places a flag in a position on the grid.
    """
    if (col, row) in game["revealed"]:
        return
    if (col, row) in game["flags"]:
        game["flags"].remove((col, row))
    else:
        game["flags"].add((col, row))

def new_game():
    """
    Starts a new game, resets game dictionary.
    """
    field_values["width"] = integer_input("Field width: ", 1, 35)
    field_values["height"] = integer_input("Field height: ", 1, 20)
    field_values["mines_number"] = integer_input("Number of mines: ", 1,\
        field_values["width"] * field_values["height"] - 1)
    field_values["safe_tiles_number"] =\
                field_values["width"] * field_values["height"] - field_values["mines_number"]

    game["field"] =\
        create_field(field_values["width"], field_values["height"], field_values["mines_number"])
    game["revealed"] = set()
    game["flags"] = set()
    game["game_won"] = False
    game["move_count"] = 0
    game["correct_flags"] = 0

    total_tiles = field_values["width"] * field_values["height"]
    mine_density = field_values["mines_number"] / total_tiles

    #might not be the optimal ratio.
    game["complexity"] = (9 * mine_density + (1 - (1 / total_tiles))) / 10

    print(f"Starting new game with complexity {game['complexity']:.4f}")

    game["start_time"] = datetime.now()

    sweeperlib.load_sprites("sprites")
    sweeperlib.create_window(field_values["width"] * 40, field_values["height"] * 40)
    sweeperlib.set_mouse_handler(handle_mouse)
    sweeperlib.set_draw_handler(draw_field)
    sweeperlib.start()

def statistics():
    """
    statistiscs menu
    prints the best game, the total games and the total play time
    """
    load_database()

    print("\nStatistics")
    
    print(f"\nTotal games played: {database['total_games']}\
        \nTotal play time: {formatted_time(database['total_play_time'])}")

    if database["best_game"]:
        print("\nBest Game:")
        print(f"  {database['best_game']['result']},")
        if database['best_game']['result'] == "Loss":
            print(f"  Correct flags: {database['best_game']['correct_flags']},")
        else:
            print(f"  Score: {database['best_game']['score']},")
        print(f"  Time: {formatted_time(database['best_game']['time'])},")
        print(f"  Complexity: {database['best_game']['complexity']:.4f},")
        print(f"  Dimension: {database['best_game']['dimension']},")
        print(f"  Moves: {database['best_game']['moves']},")
        print(f"  Date: {database['best_game']['date']}")
    else:
        print("\nNo best game recorded yet.")

    if integer_input("\n1. Show previous games\n2. Back\n", 1, 2) == 1:
        if database["game_history"]:
            print("\nRecent Games:")
            for count, game_data in enumerate(reversed(database["game_history"]), 1):
                print(f"{count}. Date: {game_data['date']},\n  {game_data['result']},")      
                if game_data['result'] == "Loss":
                    print(f"  Correct flags: {game_data['correct_flags']},")
                else:
                    print(f"  Score: {game_data['score']},")
                print(f"  Time: {formatted_time(game_data['time'])},\n"
                      f"  Complexity: {game_data['complexity']:.4f},\n"
                      f"  Dimension: {game_data['dimension']},\n"
                      f"  Moves: {game_data['moves']}\n")
                if count == 5:
                    break

def update_stats():
    """
    loads the game to the archive
    if the score is higher than the previous best game score sets the game as the best game
    updates the play time and games counter
    """
    database["total_games"] += 1
    database["total_play_time"] += game["elapsed_time"]

    current_game_stats = {
        "score": game["score"],
        "dimension":\
            f"{field_values['width']}x{field_values['height']}x{field_values['mines_number']}",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "time": game["elapsed_time"],
        "complexity": game["complexity"],
        "result": game["final_result"],
        "moves": game["move_count"],
        "correct_flags": game["correct_flags"]
    }

    if not database["best_game"] or game["score"] > database["best_game"]["score"]:
        database["best_game"] = current_game_stats

    database["game_history"].append(current_game_stats)

    with open("minesweeper_stats.json", "w") as file:
        json.dump(database, file, indent=4)

def formatted_time(time_in_seconds):
    """
    format time from seconds to a more readable factor
    """
    hours, remainder = divmod(time_in_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours == 0:
        if minutes == 0:
            if seconds == 1:
                return f"{seconds} second"
            if seconds == 0:
                return "None"
            return f"{seconds} seconds"
        return f"{minutes} minutes, {seconds} seconds"       
    return f"{hours} hours, {minutes} minutes, {seconds} seconds"

def integer_input(text, minimum = 1, maximum = 1000):
    """
    prompts for an integer, between two values
    """
    while True:
        try:
            user_input = int(input(text))
        except ValueError:
            print("Insert only numbers.")
        else:
            if minimum <= user_input <= maximum:
                return user_input
            print(f"Insert a number between {minimum} and {maximum}.")

def main():
    """
    main menu loop
    """
    print("Welcome to \"Minesweeper\"\nAuthor: Piero Cianciotta\nCourse: Elementary Programming")

    database = load_database()

    while True:
        ch = integer_input("\nMinesweeper: \n1. New game\n2. Show Statistics\n3. Quit\n", 1, 3)
        if ch == 1:
            new_game()
        elif ch == 2:
            statistics()
        elif ch == 3:
            print("Goodbye.")
            break


if __name__ == "__main__":
    main()

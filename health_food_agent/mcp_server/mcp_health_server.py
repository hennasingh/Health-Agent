from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("Health-Service")

storage = {
    "steps": 0
}


def _fetch_calories(food: str) -> tuple[str, str]:
    """
    Internal helper to fetch calorie data from Open Food Facts with fallback logic.
    Returns: (result_text, query_used)
    """
    original_query = food.lower().strip()
    # Filter out common stop-words to create more effective fallback queries
    stop_words = {"and", "with", "for", "of", "the", "&", "in", "a", "an"}
    words = [w for w in original_query.split() if w not in stop_words]
    
    if not words:
        return None, None

    # Build a priority list of queries
    queries = [original_query]
    
    if len(words) == 1:
        # For single words, prioritize finding the "raw" vegetable/meat version
        queries.insert(0, f"raw {words[0]}")
        queries.append(f"whole {words[0]}")
    elif len(words) >= 2:
        # Try the filtered phrase (e.g. "lamb potato pie" instead of "lamb and potato pie")
        filtered_phrase = " ".join(words)
        if filtered_phrase != original_query:
            queries.append(filtered_phrase)
            
        # Try first + last word (e.g. "lamb pie" from "lamb and potato pie")
        if len(words) >= 3:
            queries.append(f"{words[0]} {words[-1]}")
            
        # Try first two words (e.g. "lamb potato")
        queries.append(" ".join(words[:2]))
        
        # Individual word fallbacks
        queries.append(words[0])
        queries.append(words[-1])

    # De-duplicate queries while preserving order
    seen = set()
    unique_queries = [x for x in queries if not (x in seen or seen.add(x))]

    for query in unique_queries:
        try:
            # Use a more common User-Agent to prevent anonymous request blocking
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(
                "https://world.openfoodfacts.org/cgi/search.pl",
                params={
                    "search_terms": query,
                    "search_simple": 1,
                    "action": "process",
                    "json": 1,
                    "page_size": 15,
                    "fields": "product_name,generic_name,nutriments",
                },
            headers=headers,
                timeout=10,
            )
            
            if response.status_code != 200:
                continue
            
            try:
                data = response.json()
            except (ValueError, requests.exceptions.JSONDecodeError):
                continue
                
            products = data.get("products", [])
            if not products:
                continue

            for product in products:
                nutriments = product.get("nutriments", {})
                
                # Look for calories in multiple possible keys
                kcal = (
                    nutriments.get("energy-kcal_100g")
                    or nutriments.get("energy-kcal")
                    or nutriments.get("energy-kcal_value")
                    or nutriments.get("energy-kcal_serving")
                )
                
                # Fallback: Convert kJ to kcal if kcal is missing (1 kJ = 0.239 kcal)
                if kcal is None:
                    kj = nutriments.get("energy-kj_100g") or nutriments.get("energy-kj")
                    if kj:
                        try:
                            kcal = round(float(kj) * 0.239, 1)
                        except:
                            pass
                
                if kcal is not None:
                    name = product.get("product_name") or product.get("generic_name") or query
                    return f"{name} contains approximately {kcal} kcal per 100g.", query
        except Exception:
            continue
    return None, None


@mcp.tool()
def get_calories(food: str) -> str:
    """Fetch calorie data from Open Food Facts."""
    result, _ = _fetch_calories(food)
    if result:
        return result
    return f"Could not find specific calorie data for '{food}' on Open Food Facts."


@mcp.tool()
def get_recipe(ingredient: str, cuisine: str = "") -> str:
    """Fetch recipe ideas from TheMealDB."""

    ingredient = ingredient.lower().strip()
    cuisine = cuisine.strip()

    try:
        # Try ingredient search first
        ingredient_response = requests.get(
            "https://www.themealdb.com/api/json/v1/1/filter.php",
            params={"i": ingredient},
            headers={"User-Agent": "HealthFoodAgent/1.0 (https://github.com/arya/Health-Agent)"},
            timeout=10,
        ).json()

        if ingredient_response.get("meals"):
            meals = ingredient_response["meals"][:3]
            names = ", ".join(meal["strMeal"] for meal in meals)
            return f"Recipe ideas using {ingredient}: {names}"

        # Try meal name search
        search_response = requests.get(
            "https://www.themealdb.com/api/json/v1/1/search.php",
            params={"s": ingredient},
            headers={"User-Agent": "HealthFoodAgent/1.0 (https://github.com/arya/Health-Agent)"},
            timeout=10,
        ).json()

        if search_response.get("meals"):
            meals = search_response["meals"][:3]
            names = ", ".join(meal["strMeal"] for meal in meals)
            return f"Recipe ideas related to {ingredient}: {names}"

        # Try cuisine search if cuisine was given
        if cuisine:
            cuisine_response = requests.get(
                "https://www.themealdb.com/api/json/v1/1/filter.php",
                params={"a": cuisine},
                headers={"User-Agent": "HealthFoodAgent/1.0 (https://github.com/arya/Health-Agent)"},
            timeout=10,
            ).json()

            if cuisine_response.get("meals"):
                meals = cuisine_response["meals"][:3]
                names = ", ".join(meal["strMeal"] for meal in meals)
                return (
                    f"I could not find an exact {ingredient} recipe, "
                    f"but here are {cuisine} recipe ideas: {names}"
                )

        return (
            f"TheMealDB could not find a recipe for {ingredient}. "
            f"Try chicken, egg, rice, beef, pasta, salmon, tomato, or cheese."
        )

    except Exception as error:
        return f"Could not fetch recipe data from TheMealDB: {error}"


@mcp.tool()
def get_recipe_details(meal: str) -> str:
    """Fetch full instructions and ingredients for a specific meal from TheMealDB."""
    meal = meal.strip()

    try:
        response = requests.get(
            "https://www.themealdb.com/api/json/v1/1/search.php",
            params={"s": meal},
            headers={"User-Agent": "HealthFoodAgent/1.0 (https://github.com/arya/Health-Agent)"},
            timeout=10,
        ).json()

        meals = response.get("meals")
        if not meals:
            return f"Could not find detailed instructions for '{meal}'."

        # Get the first match
        m = meals[0]
        name = m.get("strMeal")
        instructions = m.get("strInstructions")
        
        # Collect ingredients (TheMealDB uses strIngredient1, strMeasure1, etc.)
        ingredients = []
        for i in range(1, 21):
            ing = m.get(f"strIngredient{i}")
            meas = m.get(f"strMeasure{i}")
            if ing and ing.strip():
                ingredients.append(f"- {meas} {ing}")
        
        ingredient_list = "\n".join(ingredients)
        
        # Also try to fetch calorie context for the meal name
        calorie_context, query_used = _fetch_calories(name)
        if calorie_context:
            if query_used.lower() != name.lower().strip():
                nutrition_section = f"\n\nNutrition Context: Specific data for '{name}' was not found. Showing data for '{query_used}' instead:\n{calorie_context}"
            else:
                nutrition_section = f"\n\nNutrition Context (est.):\n{calorie_context}"
        else:
            nutrition_section = f"\n\nNutrition Context: Specific calorie data for '{name}' was not found in Open Food Facts."
        
        return (
            f"Recipe: {name}\n\n"
            f"Ingredients:\n{ingredient_list}\n\n"
            f"Instructions:\n{instructions}"
            f"{nutrition_section}"
        )

    except Exception as error:
        return f"Could not fetch details for {meal}: {error}"


@mcp.tool()
def manage_steps(action: str, value: int = 0) -> str:
    """Manage step count. action can be add, get, or reset."""

    action = action.lower().strip()

    if action == "add":
        if value <= 0:
            return "Please provide a positive number of steps."

        storage["steps"] += value
        return f"Added {value} steps. Current total: {storage['steps']} steps."

    if action == "get":
        return f"Current step total: {storage['steps']} steps."

    if action == "reset":
        storage["steps"] = 0
        return "Step count reset to 0."

    return "Invalid action. Use add, get, or reset."


if __name__ == "__main__":
    mcp.run()
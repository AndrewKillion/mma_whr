# Whole History Rating (WHR) for MMA

This Python library is a conversion and modification from the original Ruby implementation of Rémi Coulom's Whole-History Rating (WHR) algorithm, designed to provide a dynamic rating system for MMA fights where fighters' skills are continuously estimated over time.

The original Ruby code is available at goshrine. The python conversion this is based on is available at https://github.com/pfmonville/whole_history_rating.

## What is an Whole History Rating?

Whole History Rating (WHR) was originally designed by [Rémi Coulom](https://www.remi-coulom.fr/WHR/) as new version of ELO ratings.

#### What is an ELO rating system?
[ELO](https://en.wikipedia.org/wiki/Elo_rating_system) was designed by Arpad Elo has a way to rank chess players. In brief:
- Players have scores that reflect how "likely" a player is to win relative to their opponent.
    - Traditionally a difference of 100 points reflects a 64% chance the higher rated player wins.
- The winning player "takes" an amount of points from the losing player.
- The amount that's taken depends on how different the ratings are.
    - If both players are 1500; The winner's post-match rating will be 1510 and the loser will be 1490
    - If the winning player's pre-match rating is 1300 and the loser is 1600; The winner's post-match rating will be 1317 and the loser will be 1583
    - Conversely, if the winning player's pre-match rating is 1600 and the loser is 1300; The winner's post-match rating will be 1603 and the loser will be 1297
       - **Note:** that a higher rated player will "take" less points from a lower rated player in the event of a win. Why? Because they were expected to win and shouldn't rewarded for beating "lesser" opponents.

Since the initial ELO ratings there have been a variety of different version: [GLICKO](https://en.wikipedia.org/wiki/Glicko_rating_system), [GLICKO-2](https://glicko.net/glicko/glicko2.pdf), [TrueSkill](https://en.wikipedia.org/wiki/TrueSkill), 


#### What makes WHR different?
In brief, WHR takes into account strength of schedule across entire history to determine the current score of everyone.

Example scenario:  Two fighters (A & B) with similar scores (say a traditional starting score like 1500) fighter each other 12 times.  They split the matches evenly both going 6-6.  Fair to say they are evenly matched.  Now, A goes on to play someone else with a much higher score (we'll say 1900) and beats him.  A has deservedly increased his rating (by ~18pts).  But what about B?  If we agreed that A and B are evenly matched shouldn't that mean that B is also likely good (even to A, right?) and also deserves an increase in score?  

What WHR aims to do is re-score everyone by working through all the past "branches" of fight histories to produce a current snapshot of what all participants current scores are.  So match wins/losses affect more than just the two participants and instead affects all the opponents in each participants history (and thus all those previous opponents opponents... and those opponents opponents... and so on...).  

Additionally, it has a time decaying function (that's adjustable here) to account for skill changes over time.  Beating a world champion when they were just starting out will have far less impact than beating a world champion at the top of their game.

## Getting Started

To install the library, use the following command:

```bash
pip install whole-history-rating
```

## Usage

### Basic Setup

Start by importing the library and initializing the base WHR object:

```python
from whr import whole_history_rating

whr = whole_history_rating.Base()
```

### Creating Fights

Add fights to the system using `create_fight()` method. It takes the names of the fighter 1 and fighter 2, the winner ('one' for fighter_1, 'two' for fighter_2), the day number, the method of victory [0: KO, 1: Split Decision, 2: Submission, 3: Unanmious Decision] and an optional handicap (#TODO: I'm working on incorprating odds as handicaps).

```python
whr.create_fight("khabib", "mcgregor", "one", 1, 2, 0)
whr.create_fight("khabib", "poirier",  "one", 2, 3, 0)
whr.create_fight("khabib", "gaethje",  "one", 3, 2, 0)
```

### Outcome weights (method of victory)

Wins are not all equal. Each fight uses a multiplier `c` on the method of victory when WHR updates ratings (higher = more rating movement through the history graph).

**Anchor:** unanimous decision (key `3`) is fixed at **`1.0`**. Other outcomes are relative to that (only ratios matter). Defaults are **neutral** — all methods start at `1.0` until you tune or search.

| Outcome | Key | Current Weights `c` |
|---------|-----|-------------|
| KO/TKO | 0 | 1.4 |
| Submission | 2 | 1.2 |
| Unanimous decision | 3 | 1.0 (anchor) |
| Split / majority decision | 1 | 1.0 |

Search weights on held-out fights (train on past, predict forward; UD stays at 1.0):

```bash
python scripts/fit_outcome_weights.py --source local --iterations 30
```

Override manually or from search output JSON:

```python
from fight_whr.outcome_weights import build_outcome_weights

weights = build_outcome_weights(ko=1.2, split=0.5, submission=1.1)  # UD -> 1.0
whr = Base(config={"outcome_weights": weights})
```

Or pass a JSON file to `scripts/load_and_iterate.py` with `--outcome-weights path/to/weights.json` (keys `0`–`3`; values are rescaled so key `3` = 1.0).

### Get Quick Info in the Terminal

By default the loader pulls **all** fights (no `LIMIT`). Use `--limit N` only for a smaller slice (oldest N by `fight_date`).

#### Look up a specific fighter's ranking and WHR Current Rating and Rating History:

```bash
python scripts/load_and_iterate.py --fighter "Alex Pereira"
```

#### Hypothetical matchup (uses each fighter's most recent rating):

```bash
python scripts/load_and_iterate.py --matchup "Ciryl Gane" "Alex Pereira"
```

Optional Elo handicap (positive favors the first fighter):

```bash
python scripts/load_and_iterate.py --matchup "Fighter A" "Fighter B" --handicap 50
```

Partial names work if the match is unique; otherwise the CLI lists candidates.

## Generating WHR Rankings in Scripts

#### RECOMMENDED: Automatic Iteration

The algorithm will automatically iterate until the ratings stabilize within a specified precision. Automatic iteration is useful when dealing with large datasets or when seeking to automate the rating process.

```python
whr.auto_iterate(time_limit=10, precision=1e-3, batch_size=10)
```

*   `time_limit` (optional): Sets a maximum duration (in seconds) for the iteration process. If `None` (the default), the algorithm will run indefinitely until the specified precision is achieved.
*   `precision` (optional): Defines the desired level of accuracy for the ratings' stability. The default value is `0.001`, indicating that iteration will stop when changes between iterations are less than or equal to this threshold.
*   `batch_size` (optional): Determines the number of iterations to perform before checking for convergence and, if a `time_limit` is set, before evaluating whether the time limit has been reached. The default value is `10`, balancing between frequent convergence checks and computational efficiency.

This automated process allows the algorithm to efficiently converge to stable ratings, adjusting the number of iterations dynamically based on the complexity of the data and the specified precision and time constraints.

### Refining Ratings Towards Stability

To achieve accurate and stable ratings, the WHR algorithm allows for iterative refinement. This process can be controlled manually or handled automatically to adjust fighter ratings until they reach a stable state.

#### Manual Iteration

For manual control over the iteration process, specify the number of iterations you wish to perform. This approach gives you direct oversight over the refinement steps.

```python
whr.iterate(50)
```

This command will perform 50 iterations, incrementally adjusting fighter ratings towards stability with each step.



### Viewing Ratings

Retrieve and view fighter ratings, which include the day number, elo rating, and uncertainty:

```python
# Example output for whr.ratings_for_fighter("khabib")
print(whr.ratings_for_fighter("khabib"))
# Output:
#   [[1, -43, 0.84], 
#    [2, -45, 0.84], 
#    [3, -45, 0.84]]

# Example output for whr.ratings_for_fighter("conor")
print(whr.ratings_for_fighter("conor"))
# Output:
#   [[1, 43, 0.84], 
#    [2, 45, 0.84], 
#    [3, 45, 0.84]]
```

You can also view or retrieve all ratings in order:

```python
whr.print_ordered_ratings(current=False)  # Set `current=True` for the latest rankings only.
ratings = whr.get_ordered_ratings(current=False, compact=False)  # Set `compact=True` for a condensed list.
```

### Predicting Match Outcomes

Predict the outcome of future matches, including between non-existent fighters:

```python
# Example of predicting a future match outcome
probability = whr.probability_future_match("khabib", "conor", 0)
print(f"Win probability: khabib: {probability[0]*100}%; conor: {probability[1]*100}%")
# Output:
#   Win probability: khabib: 37.24%; conor: 62.76%
#   (0.3724317501643667, 0.6275682498356332)
```

### Enhanced Batch Loading of Fights

This feature facilitates the batch loading of multiple fights simultaneously by accepting a list of strings, where each string encapsulates the details of a single fight. To accommodate names with both first and last names and ensure flexibility in data formatting, you can specify a custom separator (e.g., a comma) to delineate the fight attributes.

#### Standard Loading

Without specifying a separator, the default space (' ') is used to split the fight details:

```python
whr.load_fights([
    "khabib conor one 1 2 0",
    "khabib poirier one 2 3 0",
    "khabib gaethje one 3 2 0"
])
```

#### Custom Separator for Complex Names

When fight details include names with spaces, such as first and last names, utilize the `separator` parameter to define an alternative delimiter, ensuring the integrity of each data point:

```python
whr.load_fights([
    "Georges St-Pierre,Matt Hughes,one,1,0",
    "Anderson Silva,Vitor Belfort,one,2,0"
], separator=",")
```

This method allows for a clear and error-free way to load fight data, especially when fighter names or fight details include spaces, providing a robust solution for managing diverse datasets.

### Saving and Loading States

Save the current state to a file and reload it later to avoid recalculating:

```python
whr.save_base('path_to_save.whr')
whr2 = whole_history_rating.Base.load_base('path_to_save.whr')
```

## Optional Configuration

Adjust the `w2` parameter, which influences the variance of rating change over time, allowing for faster or slower progression. The default is set to 300, but Rémi Coulom used a value of 14 in his paper to achieve his results.

```python
whr = whole_history_rating.Base({'w2': 14})
```

Enable case-insensitive fighter names to treat "khabib" and "Khabib" as the same entity:

```python
whr = whole_history_rating.Base({'uncased': True})
```

## Loading from mma-insights (GCP)

1. Start the Cloud SQL instance and Auth Proxy (`CLOUD_SQL_HOST=localhost` in `.env`).
2. Copy `.env.example` to `.env` and fill in credentials.
3. Install: `pip install -e .`
4. Check DB: `python scripts/ensure_db.py`
5. Load and iterate:

```bash
python scripts/load_and_iterate.py --source postgres
python scripts/load_and_iterate.py --source auto
```

`--source` is `auto` (Postgres then GCS fallback), `postgres`, `gcs`, or `local`. Fights use `fighter_a`, `fighter_b`, `date`, `winner`, and method of victory.

### Offline local snapshot

The primary Cloud SQL query lives in [`fight_whr/data/sql/ufc_fight_data.sql`](fight_whr/data/sql/ufc_fight_data.sql). Export a parquet copy once while online:

```bash
python scripts/ensure_db.py
python scripts/export_fights_snapshot.py
```

Default output: `data/local/ufc_fights.parquet` (gitignored). Optional `--limit N` or `--output /path/to/file.parquet`.

**Remote (Cloud SQL):**

```bash
python scripts/ensure_db.py
python scripts/load_and_iterate.py --source postgres
```

**Local (no network):**

```bash
python scripts/load_and_iterate.py --source local
```

Use `--local-fights /path/to/ufc_fights.parquet` or set `MMA_WHR_LOCAL_FIGHTS_PATH` in `.env` for a custom snapshot path. Re-run `export_fights_snapshot.py` when you want fresh data from the database.


## Upcoming Changes
- Different starting values based on fighter weightclass
- Larger variance in score to reflect uncertainty
- Using gambling odds as a handicap
- Progressive train/test environments


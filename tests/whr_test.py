import copy
import sys
import os
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))
from fight_whr import whole_history_rating
from fight_whr import utils


def setup_fight_with_elo(fighter_a_elo, fighter_b_elo, handicap):
    whr = whole_history_rating.Base()
    fight = whr.create_fight("fighter_a", "fighter_b", "A", 1, handicap)
    fight.fighter_b.days[0].elo = fighter_b_elo
    fight.fighter_a.days[0].elo = fighter_a_elo
    return fight


def test_even_fight_between_equal_strength_fighters_should_have_fighter_a_winrate_of_50_percent():
    fight = setup_fight_with_elo(500, 500, 0)
    assert abs(0.5 - fight.fighter_a_win_probability()) <= 0.0001


def test_even_fight_between_equal_strength_fighters_should_have_fighter_a_winrate_of_50_percent():
    fight = setup_fight_with_elo(2000, 700, 0)  # Assuming this sets up the fight with Elo ratings
    probability = fight.fighter_a_win_probability()  # Call the method to get the probability
    print(probability)  # Print the probability for debugging
    return probability

# Call the test function
result = test_even_fight_between_equal_strength_fighters_should_have_fighter_a_winrate_of_50_percent()
print(f"Fighter A win probability: {result}")


def test_handicap_should_confer_advantage():
    fight = setup_fight_with_elo(500, 500, 1)
    assert fight.fighter_b_win_probability() > 0.5


def test_higher_rank_should_confer_advantage():
    fight = setup_fight_with_elo(600, 500, 0)
    assert fight.fighter_a_win_probability() > 0.5


def test_winrates_are_equal_for_same_elo_delta():
    fight = setup_fight_with_elo(100, 200, 0)
    fight2 = setup_fight_with_elo(200, 300, 0)
    assert abs(fight.fighter_a_win_probability() - fight2.fighter_a_win_probability()) <= 0.0001


def test_winrates_for_twice_as_strong_fighter():
    fight = setup_fight_with_elo(100, 200, 0)
    assert abs(0.359935 - fight.fighter_a_win_probability()) <= 0.0001


def test_winrates_should_be_inversely_proportional_with_unequal_ranks():
    fight = setup_fight_with_elo(600, 500, 0)
    assert (
        abs(fight.fighter_a_win_probability() - (1 - fight.fighter_b_win_probability())) <= 0.0001
    )


def test_winrates_should_be_inversely_proportional_with_handicap():
    fight = setup_fight_with_elo(500, 500, 4)
    assert (
        abs(fight.fighter_a_win_probability() - (1 - fight.fighter_b_win_probability())) <= 0.0001
    )


def test_output():
    whr = whole_history_rating.Base()
    whr.create_fight("conor", "khabib", "B", 1, 0)
    whr.create_fight("conor", "khabib", "A", 2, 0)
    whr.create_fight("conor", "khabib", "A", 3, 0)
    whr.iterate(50)
    assert [
        (1, -43, 0.84),
        (2, -45, 0.84),
        (3, -45, 0.84),
    ] == whr.ratings_for_fighter("conor")
    assert [
        (1, 43, 0.84),
        (2, 45, 0.84),
        (3, 45, 0.84),
    ] == whr.ratings_for_fighter("khabib")


def test_output2():
    whr = whole_history_rating.Base()
    whr.create_fight("conor", "khabib", "B", 1, 0)
    whr.create_fight("conor", "khabib", "A", 2, 0)
    whr.create_fight("conor", "khabib", "A", 3, 0)
    whr.create_fight("conor", "khabib", "A", 4, 0)
    whr.create_fight("conor", "khabib", "A", 4, 0)
    whr.iterate(50)
    assert [
        (1, -92, 0.71),
        (2, -94, 0.71),
        (3, -95, 0.71),
        (4, -96, 0.72),
    ] == whr.ratings_for_fighter("conor")
    assert [
        (1, 92, 0.71),
        (2, 94, 0.71),
        (3, 95, 0.71),
        (4, 96, 0.72),
    ] == whr.ratings_for_fighter("khabib")


def test_unstable_exception_raised_in_certain_cases():
    whr = whole_history_rating.Base()
    for _ in range(10):
        whr.create_fight("anchor", "fighter", "B", 1, 0)
        whr.create_fight("anchor", "fighter", "A", 1, 0)
    for _ in range(10):
        whr.create_fight("anchor", "fighter", "B", 180, 600)
        whr.create_fight("anchor", "fighter", "A", 180, 600)
    with pytest.raises(utils.UnstableRatingException):
        whr.iterate(10)


def test_log_likelihood():
    whr = whole_history_rating.Base()
    whr.create_fight("conor", "khabib", "B", 1, 0)
    whr.create_fight("conor", "khabib", "A", 4, 0)
    whr.create_fight("conor", "khabib", "A", 10, 0)
    fighter = whr.fighters["conor"]
    fighter.days[0].r = 1
    fighter.days[1].r = 2
    fighter.days[2].r = 0
    assert abs(-69.65648196168772 - fighter.log_likelihood()) <= 0.0001
    assert abs(-1.9397850625546684 - fighter.days[0].log_likelihood()) <= 0.0001
    assert abs(-2.1269280110429727 - fighter.days[1].log_likelihood()) <= 0.0001
    assert abs(-0.6931471805599453 - fighter.days[2].log_likelihood()) <= 0.0001


def test_creating_fights():
    # test creating the base with modified w2 and uncased
    whr = whole_history_rating.Base(config={"w2": 14, "uncased": True})
    # test creating one fight
    assert isinstance(
        whr.create_fight("conor", "khabib", "B", 4, 0), whole_history_rating.Game
    )
    # test creating one fight with winner uncased (b instead of B)
    assert isinstance(
        whr.create_fight("conor", "khabib", "w", 5, 0), whole_history_rating.Game
    )
    # test creating one fight with cased letters (ShUsAkU instead of conor and ShUsAi instead of khabib)
    assert isinstance(
        whr.create_fight("cOnOr", "khaBIB", "A", 6, 0), whole_history_rating.Game
    )
    assert list(whr.fighters.keys()) == ["khabib", "conor"]


def test_loading_several_fights_at_once(capsys):
    whr = whole_history_rating.Base()
    # test loading several fights at once
    test_fights = [
        "conor; khabib; B; 1",
        "conor;khabib;A;2;0",
        " conor ; khabib ;A ; 3; {'w2':300}",
        "conor;faceless_man;B;3;0;{'w2':300}",
    ]
    whr.load_fights(test_fights, separator=";")
    assert len(whr.fights) == 4
    # test auto iterating to get convergence
    whr.iterate(20)
    # test getting ratings for fighter conor (day, elo, uncertainty)
    assert whr.ratings_for_fighter("conor") == [
        (1, 26.0, 0.70),
        (2, 25.0, 0.70),
        (3, 24.0, 0.70),
    ]
    # test getting ratings for fighter khabib, only current elo and uncertainty
    assert whr.ratings_for_fighter("khabib", current=True) == (87.0, 0.84)
    # test getting probability of future match between conor and faceless_man2 (which default to 1 win 1 loss)
    assert whr.probability_future_match("khabib", "faceless_man2", 0) == (
        0.6224906898220315,
        0.3775093101779684,
    )
    display = "win probability: khabib:62.25%; faceless_man2:37.75%\n"
    captured = capsys.readouterr()
    assert display == captured.out
    # test getting log likelihood of base
    assert whr.log_likelihood() == 0.7431542354571272
    # test printing ordered ratings
    whr.print_ordered_ratings()
    display = "faceless_man => [-112.37545390067574]\nconor => [25.552142942931102, 24.669738398550702, 24.49953062693439]\nkhabib => [84.74972643795506, 86.17200033461006, 86.88207745833284]\n"
    captured = capsys.readouterr()
    assert display == captured.out
    # test printing ordered ratings, only current elo
    whr.print_ordered_ratings(current=True)
    display = "faceless_man => -112.37545390067574\nconor => 24.49953062693439\nkhabib => 86.88207745833284\n"
    captured = capsys.readouterr()
    assert display == captured.out
    # test getting ordered ratings, compact form
    assert whr.get_ordered_ratings(compact=True) == [
        [-112.37545390067574],
        [25.552142942931102, 24.669738398550702, 24.49953062693439],
        [84.74972643795506, 86.17200033461006, 86.88207745833284],
    ]
    # test getting ordered ratings, only current elo with compact form
    assert whr.get_ordered_ratings(compact=True, current=True) == [
        -112.37545390067574,
        24.49953062693439,
        86.88207745833284,
    ]
    # test saving base
    whole_history_rating.Base.save_base(whr, "test_whr.pkl")
    # test loading base
    whr2 = whole_history_rating.Base.load_base("test_whr.pkl")
    # test inspecting the first fight
    whr_fights = [str(x) for x in whr.fights]
    whr2_fights = [str(x) for x in whr2.fights]
    assert whr_fights == whr2_fights


def test_save_and_load():
    whr = whole_history_rating.Base(
        config={"w2": 1000, "uncased": True, "debug": True, "extra_parameter": "hello"}
    )
    whole_history_rating.Base.save_base(whr, "test_whr.pkl")
    whr2 = whole_history_rating.Base.load_base("test_whr.pkl")
    assert whr.config == whr2.config


def test_auto_iterate(capsys):
    whr = whole_history_rating.Base()
    # test loading several fights at once
    test_fights = [
        "conor; khabib; B; 1",
        "conor;khabib;A;2;0",
        " conor ; khabib ;A ; 3; {'w2':300}",
        "conor;faceless_man;B;3;0;{'w2':300}",
    ]
    whr.load_fights(test_fights, separator=";")
    # test auto iterating to get convergence
    whr1 = copy.deepcopy(whr)
    whr2 = copy.deepcopy(whr)
    whr3 = copy.deepcopy(whr)
    whr4 = copy.deepcopy(whr)
    whr5 = copy.deepcopy(whr)
    iterations1, is_stable1 = whr1.auto_iterate(batch_size=1)
    assert iterations1 == 12
    assert is_stable1
    iterations2, is_stable2 = whr2.auto_iterate()
    assert iterations2 == 30
    assert is_stable2
    iterations3, is_stable3 = whr3.auto_iterate(precision=0.5, batch_size=1)
    assert iterations3 == 6
    assert is_stable3
    iterations4, is_stable4 = whr4.auto_iterate(precision=0.9, batch_size=1)
    assert iterations4 == 5
    assert is_stable4
    iterations5, is_stable5 = whr5.auto_iterate(time_limit=1, batch_size=1)
    assert iterations5 == 12
    assert is_stable5


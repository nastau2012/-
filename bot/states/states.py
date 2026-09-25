"""FSM-состояния."""

from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    gender = State()
    age = State()
    height = State()
    weight = State()
    activity = State()
    goal = State()


class AddMeal(StatesGroup):
    meal_type = State()
    search = State()
    choose_product = State()
    weight = State()
    confirm = State()


class EditMeal(StatesGroup):
    choose = State()
    field = State()
    value = State()


class AddProduct(StatesGroup):
    name = State()
    category = State()
    calories = State()
    protein = State()
    fat = State()
    carbs = State()


class SearchProduct(StatesGroup):
    query = State()


class WeightLog(StatesGroup):
    weight = State()


class TemplateCreate(StatesGroup):
    name = State()
    product_search = State()
    product_weight = State()


class EditProfile(StatesGroup):
    field = State()
    value = State()

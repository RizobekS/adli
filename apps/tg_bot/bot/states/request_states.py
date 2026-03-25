from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    choosing_language = State()
    waiting_for_contact = State()
    waiting_for_phone_fallback_action = State()


class RegistrationStates(StatesGroup):
    waiting_for_inn = State()
    waiting_for_company_name = State()
    choosing_region = State()
    choosing_district = State()
    waiting_for_fio = State()
    choosing_category = State()
    choosing_directions = State()
    confirming = State()


class RequestCreateStates(StatesGroup):
    choosing_problem_direction = State()
    typing_description = State()
    uploading_files = State()
    confirming = State()
from flask import Blueprint

from flask_restful import Api, Resource, reqparse

from uranus_middleware.auth_utils import get_user_id, passenger_required
from uranus_middleware.endpoints.counter import counter
from uranus_middleware.models.boarding_pass import Pass as BoardingPassModel
from uranus_middleware.models.counter_service import counter_service
from uranus_middleware.models.passenger import Passenger as PassengerModel
from uranus_middleware.models.user import filter_information

checkin_blueprint = Blueprint('checkin', __name__)
checkin_api = Api(checkin_blueprint)


class CheckIn(Resource):

    @passenger_required
    def post(self):
        parser = reqparse.RequestParser()
        print('a')
        parser.add_argument('number_of_luggages', required=True)
        parser.add_argument('accompanying_persons', type=list, required=True, location='json')
        data = parser.parse_args()
        print(data)
        user_id = get_user_id()
        number_of_luggages = int(data['number_of_luggages']) or 0
        fellow_id_numbers = data['accompanying_persons']
        all_user = PassengerModel.find()  # don't wanna send multiple requests for each of the fellows :(
        fellows = list(filter(lambda x: x.get('user', {}).get('id_number') in
                              fellow_id_numbers or x.get('user', {}).get('id') == user_id, all_user))
        counter_id = counter_service.allocate_counter(number_of_luggages, fellows)
        counter_service.length_add(counter_id)
        # send ws message to counter staff
        all_boarding_pass = BoardingPassModel.find()
        info_objects = []
        for passenger in fellows:
            user = passenger.get('user', {})
            boarding_pass = next(filter(lambda x: x.get('passenger', {}).get('id') == passenger.get('id'), all_boarding_pass))
            info = {
                'information': {
                    **filter_information(user),
                    'id': passenger.get('id')  # need this id for add luggage requests later
                },
                'spec': {
                    'compartment_code': boarding_pass.get('compartment_code'),
                    'seat_number': boarding_pass.get('seat_number')
                }
            }
            info_objects.append(info)

        ws_data = {
            'type': 'passenger',
            'message': info_objects
        }
        counter.notify(counter_id, ws_data)
        return {
            'counter_id': counter_id
        }


checkin_api.add_resource(CheckIn, '/checkin')
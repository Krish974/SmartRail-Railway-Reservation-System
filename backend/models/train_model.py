from backend.utils.db_connection import execute_query
from backend.services.railway_service import RailwayService

class TrainModel:
    @staticmethod
    def get_all_stations():
        return RailwayService.get_all_stations()

    @staticmethod
    def search_stations(query, limit=10):
        return RailwayService.search_stations(query, limit=limit)

    @staticmethod
    def get_all_trains():
        sql = """
            SELECT t.*, 
                   s1.code as source_code, s1.name as source_name, s1.city as source_city,
                   s2.code as dest_code, s2.name as dest_name, s2.city as dest_city
            FROM trains t
            JOIN stations s1 ON t.source_station_id = s1.id
            JOIN stations s2 ON t.dest_station_id = s2.id
            ORDER BY t.train_number ASC
        """
        return execute_query(sql, fetchall=True)

    @staticmethod
    def get_by_id(train_id):
        sql = """
            SELECT t.*, 
                   s1.code as source_code, s1.name as source_name, s1.city as source_city,
                   s2.code as dest_code, s2.name as dest_name, s2.city as dest_city
            FROM trains t
            JOIN stations s1 ON t.source_station_id = s1.id
            JOIN stations s2 ON t.dest_station_id = s2.id
            WHERE t.id = %s
        """
        train = execute_query(sql, (train_id,), fetchone=True)
        if not train:
            return None
        
        # Attach stops and coaches
        train['stops'] = RailwayService._get_train_stops(train_id)
        train['coaches'] = RailwayService.ensure_train_coaches(train_id)
        train['classes'] = RailwayService._enrich_train_coaches(train_id)
        return train

    @staticmethod
    def get_train_coaches(train_id, class_code=None, date=None, quota='GN'):
        return RailwayService.get_train_coach_composition(train_id, class_type=class_code, date=date, quota=quota)

    @staticmethod
    def get_by_number(train_number):
        return RailwayService.search_by_train_number(train_number)

    @staticmethod
    def search(source=None, destination=None, date=None, class_type=None, quota='GN', train_number=None, train_name=None, query=None):
        return RailwayService.unified_search(
            query=query,
            train_number=train_number,
            train_name=train_name,
            source=source,
            destination=destination,
            date=date,
            class_type=class_type,
            quota=quota
        )

    @staticmethod
    def create(train_number, train_name, source_id, dest_id, departure_time, arrival_time, duration, running_days, train_type="Superfast Express"):
        sql = """
            INSERT INTO trains (train_number, train_name, source_station_id, dest_station_id, departure_time, arrival_time, duration, running_days, train_type, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
        """
        train_id = execute_query(sql, (train_number, train_name, source_id, dest_id, departure_time, arrival_time, duration, running_days, train_type), commit=True)
        return TrainModel.get_by_id(train_id)

    @staticmethod
    def update(train_id, train_name, departure_time, arrival_time, duration, running_days, is_active=1):
        sql = """
            UPDATE trains
            SET train_name = %s, departure_time = %s, arrival_time = %s, duration = %s, running_days = %s, is_active = %s
            WHERE id = %s
        """
        execute_query(sql, (train_name, departure_time, arrival_time, duration, running_days, is_active, train_id), commit=True)
        return TrainModel.get_by_id(train_id)

    @staticmethod
    def delete(train_id):
        sql = "DELETE FROM trains WHERE id = %s"
        return execute_query(sql, (train_id,), commit=True)

waitUntil {
	!isNull (findDisplay 46)
};

object_class_map = createHashMap;
next_class_num = 0;

fuc_laser_scan = {
	params ["_center"];
	private _cameraPos = _center; 		  // 摄像机位置 
	private _horizontalFOV = 360;         // 水平视角（度）   
	private _verticalFOV = 60;            // 垂直视角（度）   
	private _angleResolution = 1;       // 角分辨率（度）   
	private _maxDistance = 100;          
	private _points_cnt = 0; 
	private _intersections = [];
	
	private _horizontalSteps = _horizontalFOV / _angleResolution;   
	private _verticalSteps = _verticalFOV / _angleResolution;   
	
	for "_i" from 0 to _horizontalSteps - 1 do {   
		private _horizontalAngle = (_i * _angleResolution) - (_horizontalFOV / 2);   
		for "_j" from 0 to _verticalSteps - 1 do {   
			private _verticalAngle = (_j * _angleResolution) - (_verticalFOV / 2);   
			
			private _dirX = cos (_horizontalAngle) * cos (_verticalAngle);   
			private _dirY = sin (_horizontalAngle) * cos (_verticalAngle);   
			private _dirZ = sin (_verticalAngle);   
			private _direction = [_dirX, _dirY, _dirZ];   
			private _endPos = _cameraPos vectorAdd (_direction vectorMultiply _maxDistance); 
			
			_point_info = [];
			_point_class_str = "";
			_min_points_info = [];
			_min_point_class_str = "";
			_min_distance = 999999;
			
			private _result_fire = lineIntersectsSurfaces [_cameraPos, _endPos, player, uav1, true, 1, "VIEW", "FIRE"];
			if (count _result_fire > 0) then {
				private _intersectionPos = (_result_fire select 0) select 0;   
				private _intersectionClass = (_result_fire select 0) select 2;
				_point_class_str = str _intersectionClass;

				_point_info = [_intersectionPos select 0, _intersectionPos select 1, _intersectionPos select 2, 0];
				_distance = _cameraPos vectorDistance _intersectionPos;
				if (_distance < _min_distance) then {
					_min_distance = _distance;
					_min_points_info = _point_info;
					_min_point_class_str = _point_class_str;
				};
			}; 
			

			// private _result_geom = lineIntersectsSurfaces [_cameraPos, _endPos, player, uav1, true, 1, "GEOM", "NONE"];   
			// if (count _result_geom > 0) then {
			// 	private _intersectionPos = (_result_geom select 0) select 0;   
			// 	private _intersectionClass = (_result_geom select 0) select 2;
			// 	_point_class_str = str _intersectionClass;

			// 	_point_info = [_intersectionPos select 0, _intersectionPos select 1, _intersectionPos select 2, 0];
			// 	_distance = _cameraPos vectorDistance _intersectionPos;
			// 	if (_distance < _min_distance) then {
			// 		_min_distance = _distance;
			// 		_min_points_info = _point_info;
			// 		_min_point_class_str = _point_class_str;
			// 	};
			// };
			
			if (count _min_points_info > 0)  then { 
				_points_cnt = _points_cnt + 1;
				_min_point_class = 0;
				if (_min_point_class_str in object_class_map) then {
					_min_point_class = object_class_map get _min_point_class_str;
				} else {
					_min_point_class = next_class_num;
					object_class_map set [_min_point_class_str, next_class_num];
					next_class_num = next_class_num + 1;
				};   
				_min_points_info set [3, _min_point_class];
				_intersections pushBack _min_points_info;  
			}; 
		};   
	};
	["pcl.send_com_message", ["Y"+str (_points_cnt)]] call py3_fnc_callExtension;

	if (count _intersections > 0) then {  
		["pcl.send_message", [_intersections]] call py3_fnc_callExtension;
		_intersections = []; 
	};

	_message = ["pcl.read_message", []] call py3_fnc_callExtension;
	while {_message select 0 == "N"} do {
		// sleep(0.001);
		_message = ["pcl.read_message", []] call py3_fnc_callExtension;
	};

	["pcl.send_com_message", ["I"+str (object_class_map)]] call py3_fnc_callExtension;
	_points_cnt
};

onEachFrame{

	_target_pos = getPosASL uav1;
	_start_time = diag_tickTime;
	_cnt = [_target_pos] call fuc_laser_scan;
	_end_time = diag_tickTime;
	hintSilent str (str (_end_time - _start_time));
};
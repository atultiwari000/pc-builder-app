-- Function to check CPU ↔ Motherboard compatibility (socket match)
DELIMITER //
CREATE FUNCTION check_cpu_motherboard_compatibility(cpu_id INT, motherboard_id INT)
RETURNS JSON DETERMINISTIC
BEGIN
    DECLARE cpu_socket VARCHAR(50);
    DECLARE mobo_socket VARCHAR(50);
    DECLARE result JSON;

    -- Get socket types
    SELECT socket_type INTO cpu_socket FROM cpus WHERE id = cpu_id;
    SELECT socket_type INTO mobo_socket FROM motherboards WHERE id = motherboard_id;
    
    -- Check compatibility
    IF cpu_socket = mobo_socket THEN
        SET result = JSON_OBJECT(
            'compatible', TRUE,
            'message', 'CPU and motherboard sockets are compatible',
            'severity', 'success'
        );
    ELSE
        SET result = JSON_OBJECT(
            'compatible', FALSE,
            'message', CONCAT('Socket mismatch: CPU uses ', cpu_socket, ', motherboard uses ', mobo_socket),
            'severity', 'error'
        );
    END IF;
    
    RETURN result;
END //
DELIMITER ;

-- Function to check Motherboard ↔ RAM compatibility
DELIMITER //
CREATE FUNCTION check_motherboard_ram_compatibility(motherboard_id INT, ram_id INT)
RETURNS JSON DETERMINISTIC
BEGIN
    DECLARE mobo_ram_type VARCHAR(20);
    DECLARE mobo_ram_slots INT;
    DECLARE mobo_max_speed INT;
    DECLARE ram_type VARCHAR(20);
    DECLARE ram_speed INT;
    DECLARE ram_modules INT;
    DECLARE result JSON;

    -- Get motherboard specs
    SELECT ram_type, ram_slots, max_ram_speed INTO mobo_ram_type, mobo_ram_slots, mobo_max_speed 
    FROM motherboards WHERE id = motherboard_id;
    
    -- Get RAM specs
    SELECT ram_type, speed, modules_in_kit INTO ram_type, ram_speed, ram_modules 
    FROM ram_modules WHERE id = ram_id;
    
    -- Check compatibility
    IF mobo_ram_type != ram_type THEN
        SET result = JSON_OBJECT(
            'compatible', FALSE,
            'message', CONCAT('RAM type mismatch: Motherboard supports ', mobo_ram_type, ', RAM is ', ram_type),
            'severity', 'error'
        );
    ELSEIF ram_modules > mobo_ram_slots THEN
        SET result = JSON_OBJECT(
            'compatible', FALSE,
            'message', CONCAT('Not enough RAM slots: Motherboard has ', mobo_ram_slots, ' slots, RAM kit has ', ram_modules, ' modules'),
            'severity', 'error'
        );
    ELSEIF ram_speed > mobo_max_speed THEN
        SET result = JSON_OBJECT(
            'compatible', FALSE,
            'message', CONCAT('RAM speed too high: Motherboard max ', mobo_max_speed, ' MHz, RAM is ', ram_speed, ' MHz'),
            'severity', 'warning'
        );
    ELSE
        SET result = JSON_OBJECT(
            'compatible', TRUE,
            'message', 'Motherboard and RAM are compatible',
            'severity', 'success'
        );
    END IF;
    
    RETURN result;
END //
DELIMITER ;

-- Function to check GPU ↔ Case compatibility (length)
DELIMITER //
CREATE FUNCTION check_gpu_case_compatibility(gpu_id INT, case_id INT)
RETURNS JSON DETERMINISTIC
BEGIN
    DECLARE gpu_length INT;
    DECLARE case_max_length INT;
    DECLARE result JSON;

    -- Get dimensions
    SELECT length_mm INTO gpu_length FROM gpus WHERE id = gpu_id;
    SELECT max_gpu_length_mm INTO case_max_length FROM cases WHERE id = case_id;
    
    -- Check compatibility
    IF gpu_length <= case_max_length THEN
        SET result = JSON_OBJECT(
            'compatible', TRUE,
            'message', CONCAT('GPU fits in case: GPU length ', gpu_length, ' mm, case max ', case_max_length, ' mm'),
            'severity', 'success'
        );
    ELSE
        SET result = JSON_OBJECT(
            'compatible', FALSE,
            'message', CONCAT('GPU too long: GPU length ', gpu_length, ' mm, case max ', case_max_length, ' mm'),
            'severity', 'error'
        );
    END IF;
    
    RETURN result;
END //
DELIMITER ;

-- Function to check Case ↔ Motherboard compatibility (form factor)
DELIMITER //
CREATE FUNCTION check_case_motherboard_compatibility(case_id INT, motherboard_id INT)
RETURNS JSON DETERMINISTIC
BEGIN
    DECLARE case_form_factors TEXT;
    DECLARE mobo_form_factor VARCHAR(20);
    DECLARE result JSON;

    -- Get form factors
    SELECT motherboard_form_factors INTO case_form_factors FROM cases WHERE id = case_id;
    SELECT form_factor INTO mobo_form_factor FROM motherboards WHERE id = motherboard_id;
    
    -- Check compatibility (using FIND_IN_SET for comma-separated list)
    IF FIND_IN_SET(mobo_form_factor, case_form_factors) THEN
        SET result = JSON_OBJECT(
            'compatible', TRUE,
            'message', CONCAT('Case supports motherboard form factor: ', mobo_form_factor),
            'severity', 'success'
        );
    ELSE
        SET result = JSON_OBJECT(
            'compatible', FALSE,
            'message', CONCAT('Case does not support motherboard form factor: ', mobo_form_factor, '. Supported: ', case_form_factors),
            'severity', 'error'
        );
    END IF;
    
    RETURN result;
END //
DELIMITER ;

-- Function to check PSU wattage requirements
DELIMITER //
CREATE FUNCTION check_psu_wattage_compatibility(psu_id INT, cpu_id INT, gpu_id INT)
RETURNS JSON DETERMINISTIC
BEGIN
    DECLARE psu_wattage INT;
    DECLARE cpu_tdp INT;
    DECLARE gpu_tdp INT;
    DECLARE gpu_recommended_psu INT;
    DECLARE total_required INT;
    DECLARE result JSON;

    -- Get power requirements
    SELECT wattage INTO psu_wattage FROM power_supplies WHERE id = psu_id;
    SELECT tdp INTO cpu_tdp FROM cpus WHERE id = cpu_id;
    SELECT tdp, recommended_psu_watts INTO gpu_tdp, gpu_recommended_psu FROM gpus WHERE id = gpu_id;
    
    -- Calculate total required (CPU + GPU + 100W headroom)
    SET total_required = COALESCE(cpu_tdp, 0) + COALESCE(gpu_tdp, 0) + 100;
    
    -- Use GPU recommended PSU if higher
    IF gpu_recommended_psu > total_required THEN
        SET total_required = gpu_recommended_psu;
    END IF;
    
    -- Check compatibility
    IF psu_wattage >= total_required THEN
        SET result = JSON_OBJECT(
            'compatible', TRUE,
            'message', CONCAT('PSU wattage sufficient: ', psu_wattage, ' W available, ', total_required, ' W required'),
            'severity', 'success'
        );
    ELSE
        SET result = JSON_OBJECT(
            'compatible', FALSE,
            'message', CONCAT('PSU wattage insufficient: ', psu_wattage, ' W available, ', total_required, ' W required'),
            'severity', 'error'
        );
    END IF;
    
    RETURN result;
END //
DELIMITER ;

-- Function to check Storage ↔ Motherboard compatibility
DELIMITER //
CREATE FUNCTION check_storage_motherboard_compatibility(storage_id INT, motherboard_id INT)
RETURNS JSON DETERMINISTIC
BEGIN
    DECLARE storage_interface VARCHAR(20);
    DECLARE storage_form_factor VARCHAR(20);
    DECLARE mobo_sata_ports INT;
    DECLARE mobo_m2_slots INT;
    DECLARE mobo_m2_pcie_slots INT;
    DECLARE result JSON;

    -- Get storage specs
    SELECT interface, form_factor INTO storage_interface, storage_form_factor 
    FROM storage_devices WHERE id = storage_id;
    
    -- Get motherboard specs
    SELECT sata_ports, m2_slots, m2_pcie_slots INTO mobo_sata_ports, mobo_m2_slots, mobo_m2_pcie_slots 
    FROM motherboards WHERE id = motherboard_id;
    
    -- Check compatibility
    IF storage_interface = 'SATA' AND mobo_sata_ports > 0 THEN
        SET result = JSON_OBJECT(
            'compatible', TRUE,
            'message', CONCAT('SATA storage compatible: Motherboard has ', mobo_sata_ports, ' SATA ports'),
            'severity', 'success'
        );
    ELSEIF storage_interface = 'PCIe' AND storage_form_factor = 'M.2' AND mobo_m2_pcie_slots > 0 THEN
        SET result = JSON_OBJECT(
            'compatible', TRUE,
            'message', CONCAT('NVMe M.2 storage compatible: Motherboard has ', mobo_m2_pcie_slots, ' M.2 PCIe slots'),
            'severity', 'success'
        );
    ELSEIF storage_interface = 'PCIe' AND storage_form_factor = 'M.2' AND mobo_m2_slots > 0 THEN
        SET result = JSON_OBJECT(
            'compatible', TRUE,
            'message', CONCAT('M.2 storage compatible: Motherboard has ', mobo_m2_slots, ' M.2 slots'),
            'severity', 'success'
        );
    ELSE
        SET result = JSON_OBJECT(
            'compatible', FALSE,
            'message', CONCAT('Storage interface not supported: ', storage_interface, ' ', storage_form_factor, ' not compatible with motherboard'),
            'severity', 'error'
        );
    END IF;
    
    RETURN result;
END //
DELIMITER ;

-- Function to check Cooler ↔ Case compatibility (height)
DELIMITER //
CREATE FUNCTION check_cooler_case_compatibility(cooler_id INT, case_id INT)
RETURNS JSON DETERMINISTIC
BEGIN
    DECLARE cooler_height INT;
    DECLARE case_max_height INT;
    DECLARE result JSON;

    -- Get dimensions
    SELECT height_mm INTO cooler_height FROM cpu_coolers WHERE id = cooler_id;
    SELECT max_cooler_height_mm INTO case_max_height FROM cases WHERE id = case_id;
    
    -- Check compatibility
    IF cooler_height <= case_max_height THEN
        SET result = JSON_OBJECT(
            'compatible', TRUE,
            'message', CONCAT('Cooler fits in case: Cooler height ', cooler_height, ' mm, case max ', case_max_height, ' mm'),
            'severity', 'success'
        );
    ELSE
        SET result = JSON_OBJECT(
            'compatible', FALSE,
            'message', CONCAT('Cooler too tall: Cooler height ', cooler_height, ' mm, case max ', case_max_height, ' mm'),
            'severity', 'error'
        );
    END IF;
    
    RETURN result;
END //
DELIMITER ;

-- Function to check Cooler ↔ CPU compatibility (socket support)
DELIMITER //
CREATE FUNCTION check_cooler_cpu_compatibility(cooler_id INT, cpu_id INT)
RETURNS JSON DETERMINISTIC
BEGIN
    DECLARE cooler_sockets TEXT;
    DECLARE cpu_socket VARCHAR(50);
    DECLARE result JSON;

    -- Get socket information
    SELECT socket_support INTO cooler_sockets FROM cpu_coolers WHERE id = cooler_id;
    SELECT socket_type INTO cpu_socket FROM cpus WHERE id = cpu_id;
    
    -- Check compatibility
    IF FIND_IN_SET(cpu_socket, cooler_sockets) THEN
        SET result = JSON_OBJECT(
            'compatible', TRUE,
            'message', CONCAT('Cooler supports CPU socket: ', cpu_socket),
            'severity', 'success'
        );
    ELSE
        SET result = JSON_OBJECT(
            'compatible', FALSE,
            'message', CONCAT('Cooler does not support CPU socket: ', cpu_socket, '. Supported: ', cooler_sockets),
            'severity', 'error'
        );
    END IF;
    
    RETURN result;
END //
DELIMITER ;

-- Comprehensive Build Compatibility Check (as a Procedure)
DELIMITER //
CREATE PROCEDURE check_build_compatibility(IN build_id INT, OUT compatibility_results JSON)
BEGIN
    DECLARE cpu_id INT DEFAULT NULL;
    DECLARE motherboard_id INT DEFAULT NULL;
    DECLARE ram_id INT DEFAULT NULL;
    DECLARE gpu_id INT DEFAULT NULL;
    DECLARE case_id INT DEFAULT NULL;
    DECLARE psu_id INT DEFAULT NULL;
    DECLARE storage_id INT DEFAULT NULL;
    DECLARE cooler_id INT DEFAULT NULL;
    DECLARE result JSON;
    DECLARE checks JSON;
    DECLARE done INT DEFAULT 0;
    DECLARE part_type VARCHAR(50);
    DECLARE part_id INT;
    DECLARE cur CURSOR FOR SELECT part_type, part_id FROM build_parts WHERE build_id = build_id;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    SET checks = JSON_ARRAY();

    -- Get all parts for the build
    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO part_type, part_id;
        IF done THEN
            LEAVE read_loop;
        END IF;
        CASE part_type
            WHEN 'cpu' THEN SET cpu_id = part_id;
            WHEN 'motherboard' THEN SET motherboard_id = part_id;
            WHEN 'ram' THEN SET ram_id = part_id;
            WHEN 'gpu' THEN SET gpu_id = part_id;
            WHEN 'case' THEN SET case_id = part_id;
            WHEN 'psu' THEN SET psu_id = part_id;
            WHEN 'storage' THEN SET storage_id = part_id;
            WHEN 'cooler' THEN SET cooler_id = part_id;
        END CASE;
    END LOOP;
    CLOSE cur;
    
    -- Check CPU ↔ Motherboard compatibility
    IF cpu_id IS NOT NULL AND motherboard_id IS NOT NULL THEN
        SET result = check_cpu_motherboard_compatibility(cpu_id, motherboard_id);
        SET checks = JSON_ARRAY_APPEND(checks, '$', JSON_OBJECT('check', 'cpu_motherboard', 'result', result));
    END IF;
    
    -- Check Motherboard ↔ RAM compatibility
    IF motherboard_id IS NOT NULL AND ram_id IS NOT NULL THEN
        SET result = check_motherboard_ram_compatibility(motherboard_id, ram_id);
        SET checks = JSON_ARRAY_APPEND(checks, '$', JSON_OBJECT('check', 'motherboard_ram', 'result', result));
    END IF;
    
    -- Check GPU ↔ Case compatibility
    IF gpu_id IS NOT NULL AND case_id IS NOT NULL THEN
        SET result = check_gpu_case_compatibility(gpu_id, case_id);
        SET checks = JSON_ARRAY_APPEND(checks, '$', JSON_OBJECT('check', 'gpu_case', 'result', result));
    END IF;
    
    -- Check Case ↔ Motherboard compatibility
    IF case_id IS NOT NULL AND motherboard_id IS NOT NULL THEN
        SET result = check_case_motherboard_compatibility(case_id, motherboard_id);
        SET checks = JSON_ARRAY_APPEND(checks, '$', JSON_OBJECT('check', 'case_motherboard', 'result', result));
    END IF;
    
    -- Check PSU wattage requirements
    IF psu_id IS NOT NULL AND (cpu_id IS NOT NULL OR gpu_id IS NOT NULL) THEN
        SET result = check_psu_wattage_compatibility(psu_id, cpu_id, gpu_id);
        SET checks = JSON_ARRAY_APPEND(checks, '$', JSON_OBJECT('check', 'psu_wattage', 'result', result));
    END IF;
    
    -- Check Storage ↔ Motherboard compatibility
    IF storage_id IS NOT NULL AND motherboard_id IS NOT NULL THEN
        SET result = check_storage_motherboard_compatibility(storage_id, motherboard_id);
        SET checks = JSON_ARRAY_APPEND(checks, '$', JSON_OBJECT('check', 'storage_motherboard', 'result', result));
    END IF;
    
    -- Check Cooler ↔ Case compatibility
    IF cooler_id IS NOT NULL AND case_id IS NOT NULL THEN
        SET result = check_cooler_case_compatibility(cooler_id, case_id);
        SET checks = JSON_ARRAY_APPEND(checks, '$', JSON_OBJECT('check', 'cooler_case', 'result', result));
    END IF;
    
    -- Check Cooler ↔ CPU compatibility
    IF cooler_id IS NOT NULL AND cpu_id IS NOT NULL THEN
        SET result = check_cooler_cpu_compatibility(cooler_id, cpu_id);
        SET checks = JSON_ARRAY_APPEND(checks, '$', JSON_OBJECT('check', 'cooler_cpu', 'result', result));
    END IF;
    
    -- Calculate overall compatibility
    SET compatibility_results = JSON_OBJECT(
        'build_id', build_id,
        'checks', checks,
        'overall_compatible', (
            SELECT NOT EXISTS (
                SELECT 1
                FROM JSON_TABLE(checks, '$[*]' COLUMNS (
                    compatible BOOLEAN PATH '$.result.compatible'
                )) AS jt
                WHERE jt.compatible = FALSE
            )
        )
    );
END //
DELIMITER ;

-- Function to get component details for a build
DELIMITER //
CREATE FUNCTION get_build_components(build_id INT)
RETURNS JSON DETERMINISTIC
BEGIN
    DECLARE result JSON;

    SET result = JSON_OBJECT();

    -- Get CPU
    SELECT JSON_MERGE_PRESERVE(result, JSON_OBJECT('cpu', JSON_OBJECT(
        'id', c.id,
        'name', c.name,
        'model', c.model,
        'price', c.price,
        'socket_type', c.socket_type,
        'tdp', c.tdp
    ))) INTO result
    FROM build_parts bp
    JOIN cpus c ON bp.part_id = c.id
    WHERE bp.build_id = build_id AND bp.part_type = 'cpu';
    
    -- Get Motherboard
    SELECT JSON_MERGE_PRESERVE(result, JSON_OBJECT('motherboard', JSON_OBJECT(
        'id', m.id,
        'name', m.name,
        'model', m.model,
        'price', m.price,
        'socket_type', m.socket_type,
        'form_factor', m.form_factor,
        'ram_type', m.ram_type,
        'ram_slots', m.ram_slots
    ))) INTO result
    FROM build_parts bp
    JOIN motherboards m ON bp.part_id = m.id
    WHERE bp.build_id = build_id AND bp.part_type = 'motherboard';
    
    -- Get RAM
    SELECT JSON_MERGE_PRESERVE(result, JSON_OBJECT('ram', JSON_OBJECT(
        'id', r.id,
        'name', r.name,
        'model', r.model,
        'price', r.price,
        'ram_type', r.ram_type,
        'speed', r.speed,
        'modules_in_kit', r.modules_in_kit
    ))) INTO result
    FROM build_parts bp
    JOIN ram_modules r ON bp.part_id = r.id
    WHERE bp.build_id = build_id AND bp.part_type = 'ram';
    
    -- Get GPU
    SELECT JSON_MERGE_PRESERVE(result, JSON_OBJECT('gpu', JSON_OBJECT(
        'id', g.id,
        'name', g.name,
        'model', g.model,
        'price', g.price,
        'length_mm', g.length_mm,
        'tdp', g.tdp,
        'recommended_psu_watts', g.recommended_psu_watts
    ))) INTO result
    FROM build_parts bp
    JOIN gpus g ON bp.part_id = g.id
    WHERE bp.build_id = build_id AND bp.part_type = 'gpu';
    
    -- Get Case
    SELECT JSON_MERGE_PRESERVE(result, JSON_OBJECT('case', JSON_OBJECT(
        'id', cs.id,
        'name', cs.name,
        'model', cs.model,
        'price', cs.price,
        'max_gpu_length_mm', cs.max_gpu_length_mm,
        'max_cooler_height_mm', cs.max_cooler_height_mm,
        'motherboard_form_factors', cs.motherboard_form_factors
    ))) INTO result
    FROM build_parts bp
    JOIN cases cs ON bp.part_id = cs.id
    WHERE bp.build_id = build_id AND bp.part_type = 'case';
    
    -- Get PSU
    SELECT JSON_MERGE_PRESERVE(result, JSON_OBJECT('psu', JSON_OBJECT(
        'id', p.id,
        'name', p.name,
        'model', p.model,
        'price', p.price,
        'wattage', p.wattage
    ))) INTO result
    FROM build_parts bp
    JOIN power_supplies p ON bp.part_id = p.id
    WHERE bp.build_id = build_id AND bp.part_type = 'psu';
    
    -- Get Storage
    SELECT JSON_MERGE_PRESERVE(result, JSON_OBJECT('storage', JSON_OBJECT(
        'id', s.id,
        'name', s.name,
        'model', s.model,
        'price', s.price,
        'interface', s.interface,
        'form_factor', s.form_factor
    ))) INTO result
    FROM build_parts bp
    JOIN storage_devices s ON bp.part_id = s.id
    WHERE bp.build_id = build_id AND bp.part_type = 'storage';
    
    -- Get Cooler
    SELECT JSON_MERGE_PRESERVE(result, JSON_OBJECT('cooler', JSON_OBJECT(
        'id', cc.id,
        'name', cc.name,
        'model', cc.model,
        'price', cc.price,
        'height_mm', cc.height_mm,
        'socket_support', cc.socket_support
    ))) INTO result
    FROM build_parts bp
    JOIN cpu_coolers cc ON bp.part_id = cc.id
    WHERE bp.build_id = build_id AND bp.part_type = 'cooler';
    
    RETURN result;
END //
DELIMITER ;
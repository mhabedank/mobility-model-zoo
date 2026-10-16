# Subjects of the library (planning list for the series file)

Feature: [spec.md](spec.md) · Research: [research.md](research.md) R2

One line per subject: `id` · prompt · aspect (3:2 unless noted). The prompt is the subject text; the series' style text is appended at render time, and the negative prompt is the series'. Every prompt puts the orange-yellow accent on one vehicle or machine, names no place, operator or brand, shows people only as small figures from behind, and for `iot` and `ai` names physical equipment only. "(016)" marks a subject whose image already exists; "reserve" marks a subject rendered only if the theme ends under its minimum. Scene and alt texts are written in the series file during implementation, one per subject.

Counts: rail 14 (4 existing) · public-road 9 · private-road 11 (1) · active 8 · water 7 · air 6 · infrastructure 16 · workshop 10 (1) · iot 12 · ai 12 → **105 subjects, 6 existing, 99 to render**, plus 10 reserves.

## rail (minimum 10)

- `regional-dawn` (016, hero-train-dawn) · an orange-yellow regional train leaving a small station at dawn, empty platform, mist over flat fields · 16:9
- `tram-interior` (016, topic-productdev-interior) · a bright empty tram interior in morning light, orange-yellow seats, sun streaks on the floor, city through the windows
- `wheelset-hall` (016, topic-condmon-wheelset) · an orange-yellow railway wheelset, two wheels on one axle, resting on steel stands in a bright maintenance hall, a small figure from behind with a tablet
- `train-window-notebook` (016, model-scout-large-window) · a notebook and pen on a train table by a sunlit window, an orange-yellow train passing outside, landscape in soft bands
- `tram-boulevard` · an orange-yellow tram gliding out of a stop on a wide boulevard at sunrise, one cyclist riding ahead into the light · 16:9
- `high-speed-viaduct` · an orange-yellow high-speed train crossing a tall concrete viaduct above a misty valley at sunrise · 16:9
- `metro-platform` · an orange-yellow metro train arriving at an underground platform, long tiled wall, a few small figures waiting seen from behind
- `freight-containers` · a long freight train with an orange-yellow locomotive pulling flat wagons loaded with containers through flat farmland at sunrise · 16:9
- `shunting-yard` · an orange-yellow shunting locomotive in a wide marshalling yard, fans of tracks, low morning light
- `mountain-rack` · an orange-yellow rack railway car climbing a steep alpine slope above a valley, snow on the peaks
- `track-maintenance` · an orange-yellow rail-mounted maintenance vehicle standing on the tracks of a closed line between tall trees, two small figures in silhouette with tools
- `depot-hall` · a railway depot hall with an orange-yellow train on the inspection pit road, tall windows, cables hanging from the ceiling
- `level-crossing` · a rural level crossing with lowered barrier arms and an orange-yellow regional train passing, a cyclist waiting seen from behind
- `pantograph` · close view of the roof of an orange-yellow train with a raised pantograph touching the overhead line against a pale morning sky
- reserve `night-train-morning` · an orange-yellow sleeper train arriving at a terminus in early morning light, long platform roof

## public-road (minimum 6)

- `bus-stop-sunrise` · a quiet bus stop at sunrise, a single small figure from behind with a bicycle, an orange-yellow bus approaching
- `articulated-bus-lane` · an orange-yellow articulated bus on a dedicated bus lane along a tree-lined avenue
- `coach-motorway` · a long orange-yellow touring coach with a high passenger deck on an empty motorway at sunrise, rolling hills · 16:9
- `trolleybus-wires` · an orange-yellow trolleybus under a web of overhead wires on a quiet city street
- `bus-depot` · a bus depot at dawn with rows of orange-yellow buses, one pulling out
- `village-minibus` · an orange-yellow minibus at a small stop in a village square, a figure with a shopping bag seen from behind
- `bus-charging` · an orange-yellow electric bus under a pantograph charging mast at a terminus
- `bus-station-roof` · a bus station with a wide curved roof, orange-yellow buses in the bays, morning light
- `tram-wash` · an orange-yellow tram in a washing hall between large brushes, water as flat shapes
- reserve `ramp-boarding` · a low-floor orange-yellow bus with its ramp folded out at a stop, a figure in a wheelchair seen from behind

## private-road (minimum 8)

- `workshop-bay` (016, topic-security-workshop) · a clean vehicle workshop bay at morning, an orange-yellow car with open hood, wiring harness and diagnostic cable, tall windows
- `car-open-road` · an orange-yellow compact car on an open road winding through rolling fields at sunrise · 16:9
- `car-charging` · an orange-yellow car at a charging post in a quiet car park, cable plugged in, trees behind
- `truck-river-bridge` · an orange-yellow articulated truck on a motorway bridge over a river at sunrise · 16:9
- `delivery-van` · an orange-yellow delivery van parked in a narrow old-town street, a courier seen from behind with a parcel
- `motorcycle-pass` · an orange-yellow motorcycle on a mountain pass road with hairpin bends
- `tractor-rural` · an orange-yellow tractor on a rural road between fields, dust in morning light
- `roundabout-above` · a roundabout seen from above with one orange-yellow car entering, geometric road markings
- `parking-deck` · a multi-storey car park deck with one orange-yellow car, ramps and concrete lines
- `camper-coast` · an orange-yellow camper van on a coastal road above the sea
- `car-sharing-row` · a row of parked car-sharing cars in navy and pale mint in a marked bay, a single orange-yellow car among them, a figure seen from behind with a key card
- reserve `taxi-rank` · an orange-yellow taxi waiting first in a rank in front of a station, no signs

## active (minimum 6)

- `riverside-cyclists` · a bike lane along a river at sunrise, two cyclists far ahead, an orange-yellow tram crossing a bridge in the distance, city skyline soft · 16:9
- `winter-cyclist` · a cyclist seen from behind on a snowy cycle path, an orange-yellow bicycle, bare trees
- `cargo-bike-canal` · a figure seen from behind pushing an orange-yellow cargo bike with a child seat along a canal
- `scooter-dock` · a row of e-scooters in navy at a docking station, a single orange-yellow e-scooter among them, in front of a glass office building
- `pedestrian-street` · a car-free pedestrian street at sunrise with long shadows, only walking figures seen from behind and a single orange-yellow bicycle leaning on a lamp post, no cars, no buses, no vans
- `bike-parking-station` · a bike parking hall with rows of racks, one orange-yellow bicycle, a station roof behind
- `footbridge-tracks` · a curved pedestrian footbridge over railway tracks, an orange-yellow train below, figures seen from behind above
- `cycle-highway` · an elevated bicycle bridge curving between buildings, only bicycles on it, one orange-yellow cyclist seen from behind, no cars
- reserve `walking-school` · a group of small figures seen from behind walking along a path to a school, an orange-yellow bicycle beside them

## water (minimum 5)

- `ferry-pier` · an orange-yellow passenger ferry arriving at a wooden pier on a calm lake
- `river-barge` · an orange-yellow cargo barge on a wide river passing under an arch bridge
- `container-terminal` · tall gantry cranes at a container terminal, one orange-yellow straddle carrier, water in the morning
- `lock-gate` · a river lock with its gates opening, an orange-yellow push boat waiting
- `harbour-pilot` · an orange-yellow pilot boat leaving a harbour mouth past a plain lighthouse
- `car-ferry-ramp` · an orange-yellow car ferry at a ramp, cars queuing seen from behind
- `ferry-deck` · the open deck of a ferry with orange-yellow benches, a figure seen from behind at the railing, coast ahead
- reserve `canal-narrowboat` · an orange-yellow narrowboat in a tree-lined canal, towpath with a cyclist seen from behind

## air (minimum 4)

- `regional-apron` · an orange-yellow turboprop regional aircraft on an apron at dawn, a tug and small figures seen from behind
- `apron-bus` · an orange-yellow apron bus beside a jet bridge, an aircraft tail above
- `control-tower` · an airport control tower against a pale morning sky, an orange-yellow aircraft taxiing below
- `helipad-roof` · an orange-yellow rescue helicopter on a hospital roof helipad at sunrise
- `cargo-drone-field` · a small orange-yellow quadcopter cargo drone with four rotors and a parcel box flying above a field, a farmhouse small in the distance
- `hangar-doors` · an orange-yellow light aircraft in a hangar with the doors open to the morning
- reserve `glider-launch` · an orange-yellow glider on a grass airfield at dawn, winch cable as a thin line

## infrastructure (minimum 14)

- `platform-canopy` · an empty station platform under a long steel canopy, an orange-yellow train at the far end
- `motorway-bridge` · a motorway bridge on tall piers spanning a valley, an orange-yellow truck crossing · 16:9
- `tunnel-portal` · a tunnel portal in a hillside with an orange-yellow train emerging, catenary masts
- `catenary-line` · a row of catenary masts and overhead lines along a straight track, an orange-yellow maintenance car far away · 16:9
- `signal-cabinet` · a grey metal signal cabinet with an open door beside the track, an orange-yellow railway signal head on a post, cables leading into the ground, no vehicles
- `intersection-lights` · an empty city intersection at sunrise with traffic lights, one orange-yellow tram crossing
- `charging-hub` · a charging hub with a solar canopy, orange-yellow charging posts in a row
- `hydrogen-station` · a hydrogen fuelling station with an orange-yellow bus at the dispenser
- `spiral-ramp` · the round spiral ramp of a multi-storey car park seen from outside, concrete, one orange-yellow car at the top
- `field-shelter` · a glass bus shelter at the edge of a field, an orange-yellow bus approaching over a hill
- `port-crane` · a large orange-yellow port crane over a quay at sunrise, a ship's hull in navy
- `road-works` · a road works site with cones and an orange-yellow excavator, fresh lane markings
- `snow-plough` · an orange-yellow snow plough truck on a mountain road at dawn, snow banks
- `control-room` · a traffic control room, a figure seen from behind at an orange-yellow desk console with buttons, a wall of abstract map screens, no vehicles
- `junction-above` · a railway junction seen from above, fanning tracks, one orange-yellow train · 16:9
- `weather-mast` · an orange-yellow road weather station mast with sensor arms beside an empty motorway, sensors as simple shapes, no vehicles
- reserve `bridge-inspection` · an orange-yellow inspection platform truck under a bridge deck, river below

## workshop (minimum 8)

- `circuit-bench` (016, model-picket-forest-bench) · a small green circuit board on a workbench by a window, an orange-yellow automotive diagnostic plug and a thin wiring harness connected to it, an oscilloscope showing a square wave trace
- `rail-pit` · a railcar standing over an inspection pit in a depot, the pit lit from below, a figure seen from behind down in the pit with a lamp, the railcar orange-yellow
- `bus-lift` · an orange-yellow bus raised on column lifts in a workshop, tool trolleys
- `brake-rig` · an orange-yellow stationary brake test rig, a single railway wheel mounted in a steel frame and spinning, workshop hall, no vehicles
- `battery-bench` · an orange-yellow battery pack on a bench, cables to a measuring rack, window light
- `engine-stand` · a bare engine block mounted on an orange-yellow wheeled test stand, exhaust pipes, round gauges without markings, workshop, no vehicles
- `tyre-drum` · a tyre test machine with a large drum, an orange-yellow wheel pressed against it
- `dyno-cell` · an orange-yellow car on dynamometer rollers in a test cell, cables and fans
- `wind-tunnel` · a wind tunnel test chamber with a toy-sized orange-yellow train model mounted on a pedestal in the centre, smoke streamlines as thin lines flowing around the model, no full-size train
- `axle-press` · a large orange-yellow hydraulic wheel press machine in a hall pressing a wheel onto a railway axle, a figure seen from behind
- reserve `paint-booth` · an orange-yellow tram body in a paint booth, soft light, masking lines

## iot (minimum 10)

- `bearing-sensor` · close view of a railway axle bearing housing with a small orange-yellow vibration sensor bolted on, a cable to a small box, a wheel behind, no whole train
- `telematics-cab` · a truck cab interior with an orange-yellow telematics box under the dashboard, road through the windshield
- `roof-antenna` · close view of the roof of a train with a flat orange-yellow antenna dome and a small antenna array, overhead line above, pale sky
- `cabinet-gateway` · an open grey trackside cabinet with an orange-yellow gateway device inside, indicator lights as small dots, cables, track behind, no vehicles
- `gantry-camera` · a camera in an orange-yellow housing mounted on a steel motorway gantry above empty lanes, no vehicles
- `lidar-roof` · an orange-yellow lidar unit on the roof of a car on a test track, cones
- `stop-air-sensor` · an orange-yellow air quality sensor on a lamp post at a bus stop
- `bridge-strain` · the underside of a steel bridge, strain sensors in small orange-yellow boxes bolted to the beams, cables, river below, no vehicles
- `hot-box-detector` · an orange-yellow trackside sensor beside the rails, train wheels passing
- `tyre-valve-sensor` · close view of a car wheel in a workshop, an orange-yellow sensor on the tyre valve, workshop floor, no whole car
- `container-tracker` · an orange-yellow tracking device on the door of a shipping container, port behind
- `charging-meter` · an orange-yellow meter box on a charging post, a cable to a car, morning shadows
- reserve `rail-temperature` · an orange-yellow rail temperature sensor clamped to a rail foot, ballast and sleepers

## ai (minimum 10)

- `edge-box-bus` · an open equipment cabinet inside a bus with an orange-yellow edge computer with cooling fins and cables, close view, no bus exterior
- `depot-rack` · a server rack with an orange-yellow front in a depot back office, a train through the window
- `workstation-window` · an orange-yellow workstation on a desk by a window, a screen with an abstract wave trace, a train yard outside
- `spectrogram-screen` · a figure seen from behind at a desk with an orange-yellow monitor showing an abstract vibration spectrogram as colour bands, workshop behind glass, no vehicles
- `inspection-rig` · an orange-yellow camera inspection rig above a train roof passing through a hall
- `windshield-assist` · the view through a windshield at sunrise, an orange-yellow car ahead, lane markings as simple overlay lines
- `tablet-trackside` · a figure seen from behind holding a tablet with an abstract chart in front of an orange-yellow locomotive
- `test-track-cones` · an orange-yellow car between cones on a test track, a camera mast
- `drone-yard` · a small orange-yellow quadcopter drone with four rotors hovering above a marshalling yard with fanning tracks, simple overlay lines
- `retrofit-bus` · an orange-yellow bus in a hall with a sensor kit being fitted, figures seen from behind with cables
- `simulator-seat` · a driving simulator with an orange-yellow seat in front of a curved screen showing an abstract road
- `compute-bench` · a small orange-yellow compute box on a workbench beside a circuit board and a sensor, window light
- reserve `camera-tram-front` · the front of an orange-yellow tram with a camera module above the windshield, depot behind

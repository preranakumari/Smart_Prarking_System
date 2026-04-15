import datetime
import http.server
import json
import socketserver

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Parking System</title>
<style>
  body{font-family:Segoe UI,Arial,sans-serif;background:#08101f;color:#f8fafc;margin:0;padding:0;display:flex;justify-content:center;min-height:100vh}
  .page{width:min(1000px,100%);padding:24px}
  h1{margin:0 0 12px;font-size:2.4rem;letter-spacing:-0.03em}
  .top{display:grid;gap:18px;margin-bottom:22px}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}
  .card{background:rgba(15,23,42,.95);border:1px solid rgba(148,163,184,.12);border-radius:18px;padding:18px;box-shadow:0 18px 35px rgba(0,0,0,.22)}
  .card h2{font-size:1rem;margin:0 0 12px;color:#e2e8f0}
  .stat{font-size:2rem;margin-bottom:4px}
  button,input,select{width:100%;font:inherit;border-radius:14px;border:1px solid rgba(148,163,184,.18);padding:12px 14px;background:#111827;color:#f8fafc}
  button{cursor:pointer;background:#7c3aed;border:none;color:#fff;transition:.18s}
  button:hover{filter:brightness(1.08)}
  .controls{display:grid;gap:12px}
  .slot{padding:14px;border-radius:16px;background:linear-gradient(180deg,#111827,#09111e);border:1px solid rgba(148,163,184,.1)}
  .slot span{display:block;color:#94a3b8;font-size:.92rem}
  .board{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px}
  .log{max-height:220px;overflow-y:auto;font-size:.95rem;line-height:1.5}
  .log p{margin:0 0 10px}
  .success{color:#86efac}.error{color:#fecaca}
</style>
</head>
<body>
<div class="page">
  <div class="top">
    <div><h1>Smart Parking System</h1><p>Python OOP demo with a simple web frontend in one file.</p></div>
    <div class="card"><p>Run <code>python smart_parking_system.py</code> and open <code>http://localhost:8000</code>.</p></div>
  </div>
  <div class="grid">
    <div class="card"><h2>Overview</h2><div class="stat" id="total">0</div><span>Total slots</span></div>
    <div class="card"><h2>Available</h2><div class="stat" id="free">0</div><span>Open slots</span></div>
    <div class="card"><h2>Occupied</h2><div class="stat" id="used">0</div><span>In use</span></div>
    <div class="card"><h2>Revenue</h2><div class="stat" id="money">$0.00</div><span>Collected</span></div>
  </div>
  <div class="grid" style="margin-top:18px;">
    <div class="card controls">
      <h2>Park Vehicle</h2>
      <select id="type"><option value="bike">Bike</option><option value="car" selected>Car</option><option value="truck">Truck</option></select>
      <input id="plate" placeholder="Plate number" autocomplete="off">
      <button id="park">Park</button>
      <button id="leave" style="background:#f97316">Remove</button>
    </div>
    <div class="card">
      <h2>Slot Board</h2><div class="board" id="board"></div>
    </div>
  </div>
  <div class="card"><h2>Activity</h2><div class="log" id="log"></div></div>
</div>
<script>
const stateUrl='/state',parkUrl='/park',leaveUrl='/leave'
const E=id=>document.getElementById(id)
const log=(text,cls='')=>{const p=document.createElement('p');p.textContent=text;p.className=cls;E('log').prepend(p)}
const render=s=>{E('total').textContent=s.total_slots;E('free').textContent=s.available_slots;E('used').textContent=s.occupied_slots;E('money').textContent=`$${s.revenue.toFixed(2)}`;E('board').innerHTML=s.slots.map(x=>`<div class="slot"><strong>Slot ${x.id}</strong><span>${x.category}</span><span>${x.occupied?x.vehicle:'Available'}</span></div>`).join('')}
const post=(url,data)=>fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).then(r=>r.json())
const load=()=>fetch(stateUrl).then(r=>r.json()).then(d=>render(d.state))
E('park').onclick=()=>{const plate=E('plate').value.trim();if(!plate){log('Plate required','error');return}post(parkUrl,{type:E('type').value,plate}).then(r=>{render(r.state);log(r.message,r.success?'success':'error');if(r.success)E('plate').value=''})}
E('leave').onclick=()=>{const plate=E('plate').value.trim();if(!plate){log('Plate required','error');return}post(leaveUrl,{plate}).then(r=>{render(r.state);log(r.message,r.success?'success':'error');if(r.success)E('plate').value=''})}
load()
</script>
</body>
</html>"""

class Vehicle:
    def __init__(self, plate: str):
        self.plate = plate.upper()
        self.entered = datetime.datetime.now()

    def rate(self) -> float:
        return 1.5

    def description(self) -> str:
        return f"{self.__class__.__name__} {self.plate}"


class Bike(Vehicle):
    def rate(self) -> float:
        return 0.75


class Car(Vehicle):
    def rate(self) -> float:
        return 1.5


class Truck(Vehicle):
    def rate(self) -> float:
        return 2.4


class Slot:
    def __init__(self, slot_id: int, kind: str):
        self.id = slot_id
        self.kind = kind
        self.vehicle = None

    def occupy(self, vehicle: Vehicle) -> None:
        if self.vehicle:
            raise ValueError('slot occupied')
        self.vehicle = vehicle

    def free(self) -> Vehicle:
        if not self.vehicle:
            raise ValueError('slot empty')
        v = self.vehicle
        self.vehicle = None
        return v

    def occupied(self) -> bool:
        return self.vehicle is not None


class Ticket:
    def __init__(self, vehicle: Vehicle, slot: Slot):
        self.vehicle = vehicle
        self.slot = slot
        self.start = vehicle.entered
        self.end = None
        self.fee = 0.0

    def close(self) -> None:
        self.end = datetime.datetime.now()
        minutes = max(1, int((self.end - self.start).total_seconds() / 60))
        self.fee = round(self.vehicle.rate() * minutes * 0.1, 2)

    def summary(self) -> str:
        duration = int((self.end - self.start).total_seconds() / 60) if self.end else 0
        return f"{self.vehicle.description()} left slot {self.slot.id} after {duration} min — ${self.fee:.2f}"


class ParkingLot:
    def __init__(self, count: int = 10):
        self._slots = [Slot(i + 1, 'bike' if i < 3 else 'car' if i < 7 else 'truck') for i in range(count)]
        self._tickets = {}
        self.revenue = 0.0

    def find_slot(self, kind: str):
        for slot in self._slots:
            if slot.kind == kind and not slot.occupied():
                return slot
        return None

    def park(self, kind: str, plate: str):
        vehicle = {'bike': Bike, 'car': Car, 'truck': Truck}[kind](plate)
        slot = self.find_slot(kind)
        if not slot:
            raise ValueError(f'No {kind} slots free')
        slot.occupy(vehicle)
        ticket = Ticket(vehicle, slot)
        self._tickets[vehicle.plate] = ticket
        return ticket

    def leave(self, plate: str):
        plate = plate.upper()
        ticket = self._tickets.get(plate)
        if not ticket:
            raise ValueError('vehicle not parked')
        ticket.close()
        ticket.slot.free()
        self.revenue += ticket.fee
        del self._tickets[plate]
        return ticket

    def state(self):
        return {
            'total_slots': len(self._slots),
            'available_slots': sum(1 for s in self._slots if not s.occupied()),
            'occupied_slots': sum(1 for s in self._slots if s.occupied()),
            'revenue': self.revenue,
            'slots': [
                {
                    'id': s.id,
                    'category': s.kind,
                    'occupied': s.occupied(),
                    'vehicle': s.vehicle.description() if s.vehicle else None,
                }
                for s in self._slots
            ],
        }


class Handler(http.server.BaseHTTPRequestHandler):
    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path == '/state':
            self._json({'state': lot.state()})
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        payload = json.loads(self.rfile.read(length) or b'{}')
        try:
            if self.path == '/park':
                ticket = lot.park(payload['type'], payload['plate'])
                self._json({'success': True, 'message': f'Parked {ticket.vehicle.description()} in slot {ticket.slot.id}.', 'state': lot.state()})
            elif self.path == '/leave':
                ticket = lot.leave(payload['plate'])
                self._json({'success': True, 'message': ticket.summary(), 'state': lot.state()})
            else:
                self.send_error(404)
        except ValueError as err:
            self._json({'success': False, 'message': str(err), 'state': lot.state()}, code=400)

    def log_message(self, format, *args):
        pass


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


if __name__ == '__main__':
    lot = ParkingLot(10)
    print('Starting Smart Parking System on http://localhost:8000')
    with Server(('', 8000), Handler) as server:
        server.serve_forever()

import sys 
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QListWidget, QMessageBox, QFileDialog
)
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QPointF
import math

# --- Geometry classes ---

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def translate(self, dx, dy):
        self.x += dx
        self.y += dy

    def scale(self, sx, sy, center):
        self.x = center.x + sx * (self.x - center.x)
        self.y = center.y + sy * (self.y - center.y)

    def rotate(self, angle_deg, center):
        angle_rad = math.radians(angle_deg)
        x_shifted = self.x - center.x
        y_shifted = self.y - center.y
        x_new = x_shifted * math.cos(angle_rad) - y_shifted * math.sin(angle_rad)
        y_new = x_shifted * math.sin(angle_rad) + y_shifted * math.cos(angle_rad)
        self.x = center.x + x_new
        self.y = center.y + y_new

    def to_dict(self):
        return {'x': self.x, 'y': self.y}

    @staticmethod
    def from_dict(d):
        return Point(d['x'], d['y'])


class Polygon2:
    def __init__(self, points=None):
        self.points = points if points else []

    def translate(self, dx, dy):
        for p in self.points:
            p.translate(dx, dy)

    def scale(self, sx, sy, center):
        for p in self.points:
            p.scale(sx, sy, center)

    def rotate(self, angle_deg, center):
        for p in self.points:
            p.rotate(angle_deg, center)

    def to_dict(self):
        return {'points': [p.to_dict() for p in self.points]}

    @staticmethod
    def from_dict(d):
        pts = [Point.from_dict(pd) for pd in d['points']]
        return Polygon(pts)

    def center(self):
        if not self.points:
            return Point(0, 0)
        x_avg = sum(p.x for p in self.points) / len(self.points)
        y_avg = sum(p.y for p in self.points) / len(self.points)
        return Point(x_avg, y_avg)


class Polygon:
    def __init__(self, points=None, shape_type="polygon"):
        self.points = points if points else []
        self.type = shape_type  # nowy atrybut

    # Zmieniamy serializację:
    def to_dict(self):
        return {'points': [p.to_dict() for p in self.points], 'type': self.type}

    @staticmethod
    def from_dict(d):
        pts = [Point.from_dict(pd) for pd in d['points']]
        shape_type = d.get('type', 'polygon')
        return Polygon(pts, shape_type)


# --- Canvas widget for drawing ---

class Canvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.shapes = []
        self.selected_index = None
        self.setMinimumSize(600, 400)
        self.setMouseTracking(True)
        self.dragging_point_index = None
        self.selected_points = []

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        pen_normal = QPen(Qt.black, 2)
        pen_selected = QPen(Qt.red, 3)

        for i, shape in enumerate(self.shapes):
            pen = pen_selected if i == self.selected_index else pen_normal
            painter.setPen(pen)

            if shape.type == "circle" and len(shape.points) >= 2:
                center = shape.points[0]
                edge = shape.points[1]
                radius = math.hypot(center.x - edge.x, center.y - edge.y)
                painter.drawEllipse(QPointF(center.x, center.y), radius, radius)

            elif shape.type == "square" and len(shape.points) == 2:
                p1 = shape.points[0]
                p2 = shape.points[1]
                x0, y0 = p1.x, p1.y
                x1, y1 = p2.x, p2.y
                size = max(abs(x1 - x0), abs(y1 - y0))
                # Wyrównanie do p1 jako lewego górnego
                width = size if x1 >= x0 else -size
                height = size if y1 >= y0 else -size
                painter.drawRect(x0, y0, width, height)

            else:
                # domyślne rysowanie wielokąta
                pts = [QPointF(p.x, p.y) for p in shape.points]
                if len(pts) == 1:
                    painter.drawEllipse(pts[0], 5, 5)
                elif len(pts) > 1:
                    for j in range(len(pts)):
                        painter.drawEllipse(pts[j], 4, 4)
                        if j < len(pts) - 1:
                            painter.drawLine(pts[j], pts[j + 1])
                    if len(pts) > 2:
                        painter.drawLine(pts[-1], pts[0])

        # tymczasowe niebieskie linie
        if len(self.selected_points) >= 2:
            pen_temp = QPen(Qt.blue, 1, Qt.DashLine)
            painter.setPen(pen_temp)
            for i in range(len(self.selected_points) - 1):
                p1 = self.selected_points[i]
                p2 = self.selected_points[i + 1]
                painter.drawLine(QPointF(p1.x, p1.y), QPointF(p2.x, p2.y))

    def mousePressEvent(self, event):
        pos = event.pos()
        for i, shape in enumerate(self.shapes):
            for j, p in enumerate(shape.points):
                dist = math.hypot(p.x - pos.x(), p.y - pos.y())
                if dist < 8:
                    self.selected_index = i
                    self.dragging_point_index = j
                    self.update()
                    return
        self.selected_index = None
        self.update()

    def mouseDoubleClickEvent(self, event):
        pos = event.pos()
        for shape in self.shapes:
            for p in shape.points:
                dist = math.hypot(p.x - pos.x(), p.y - pos.y())
                if dist < 8:
                    if p not in self.selected_points:
                        self.selected_points.append(p)
                        self.update()
                    return

    def mouseMoveEvent(self, event):
        if self.dragging_point_index is not None and self.selected_index is not None:
            pos = event.pos()
            shape = self.shapes[self.selected_index]
            shape.points[self.dragging_point_index].x = pos.x()
            shape.points[self.dragging_point_index].y = pos.y()
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging_point_index = None

    def connect_selected_points(self):
        if len(self.selected_points) >= 2:
            new_shape = Polygon(self.selected_points.copy())
            self.shapes.append(new_shape)
            self.selected_points.clear()
            self.update()
            return new_shape
        return None


# --- Main Application Window ---

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Edytor grafiki wektorowej")
        self.canvas = Canvas()

        # Controls
        self.list_shapes = QListWidget()
        self.btn_add_point = QPushButton("Dodaj punkt")
        self.btn_add_polygon = QPushButton("Dodaj trójkąt")
        self.btn_add_circle = QPushButton("Dodaj okrąg")
        self.btn_add_square = QPushButton("Dodaj kwadrat")
        self.btn_connect_points = QPushButton("Połącz punkty")  # nowy przycisk
        self.btn_delete_shape = QPushButton("Usuń wybrany")
        self.btn_translate = QPushButton("Translacja")
        self.btn_scale = QPushButton("Skalowanie")
        self.btn_rotate = QPushButton("Obrót")
        self.btn_undo = QPushButton("Cofnij")
        self.btn_save = QPushButton("Zapisz do pliku")
        self.btn_load = QPushButton("Wczytaj z pliku")
        self.btn_import_points = QPushButton("Importuj z pliku")

        self.input_dx = QLineEdit("0")
        self.input_dy = QLineEdit("0")
        self.input_sx = QLineEdit("1")
        self.input_sy = QLineEdit("1")
        self.input_angle = QLineEdit("0")

        self.history = []

        self._setup_ui()
        self._connect_signals()


    def _setup_ui(self):
        layout = QHBoxLayout()
        self.setLayout(layout)

        layout.addWidget(self.canvas, 3)

        # --- Panel kontrolny w dwóch kolumnach ---
        control_panel = QHBoxLayout()
        layout.addLayout(control_panel, 1)

        left_column = QVBoxLayout()
        right_column = QVBoxLayout()
        control_panel.addLayout(left_column)
        control_panel.addLayout(right_column)

        # --- Lewa kolumna: obecne przyciski i kontrolki ---
        left_column.addWidget(QLabel("Obiekty:"))
        left_column.addWidget(self.list_shapes)
        left_column.addWidget(self.btn_add_point)
        left_column.addWidget(self.btn_add_polygon)
        left_column.addWidget(self.btn_add_circle)
        left_column.addWidget(self.btn_add_square)
        left_column.addWidget(self.btn_connect_points)
        left_column.addWidget(self.btn_delete_shape)

        left_column.addWidget(QLabel("Translacja (dx, dy):"))
        hl1 = QHBoxLayout()
        hl1.addWidget(self.input_dx)
        hl1.addWidget(self.input_dy)
        left_column.addLayout(hl1)
        left_column.addWidget(self.btn_translate)

        left_column.addWidget(QLabel("Skalowanie (sx, sy):"))
        hl2 = QHBoxLayout()
        hl2.addWidget(self.input_sx)
        hl2.addWidget(self.input_sy)
        left_column.addLayout(hl2)
        left_column.addWidget(self.btn_scale)

        left_column.addWidget(QLabel("Obrót (stopnie):"))
        left_column.addWidget(self.input_angle)
        left_column.addWidget(self.btn_rotate)
        left_column.addWidget(self.btn_undo)

        left_column.addStretch()

        # --- Prawa kolumna: nowa zawartość ---


        right_column.addWidget(self.btn_save)
        right_column.addWidget(self.btn_load)
        right_column.addWidget(self.btn_import_points)
        right_column.addStretch()



    def _connect_signals(self):
        self.btn_add_point.clicked.connect(self.add_point)
        self.btn_add_polygon.clicked.connect(self.add_polygon)
        self.btn_add_circle.clicked.connect(self.add_circle)
        self.btn_add_square.clicked.connect(self.add_square)
        self.btn_connect_points.clicked.connect(self.connect_points)  # nowy sygnał
        self.btn_delete_shape.clicked.connect(self.delete_shape)
        self.btn_translate.clicked.connect(self.translate_shape)
        self.btn_scale.clicked.connect(self.scale_shape)
        self.btn_rotate.clicked.connect(self.rotate_shape)
        self.btn_undo.clicked.connect(self.undo)
        self.btn_save.clicked.connect(self.save_to_file)
        self.btn_load.clicked.connect(self.load_from_file)
        self.list_shapes.currentRowChanged.connect(self.select_shape)
        self.canvas.mouseReleaseEvent = self.on_canvas_mouse_release
        self.btn_import_points.clicked.connect(self.import_points)

    def connect_points(self):
        new_shape = self.canvas.connect_selected_points()
        if new_shape:
            self.list_shapes.addItem("Połączone punkty")
            self.save_history()

    def add_point(self):
        p = Polygon([Point(100, 100)])
        self.canvas.shapes.append(p)
        self.list_shapes.addItem("Punkt")
        self.save_history()
        self.canvas.update()

    def add_polygon(self):
        # Dodaj prosty trójkąt na sztywno
        p = Polygon([Point(200, 200), Point(250, 200), Point(225, 150)])
        self.canvas.shapes.append(p)
        self.list_shapes.addItem("Wielokąt")
        self.save_history()
        self.canvas.update()

    def add_circle(self):
        # Okrąg na podstawie 2 punktów: środek i punkt na obwodzie
        center = Point(300, 300)
        edge = Point(350, 300)
        circle = Polygon([center, edge], shape_type="circle")
        self.canvas.shapes.append(circle)
        self.list_shapes.addItem("Okrąg")
        self.save_history()
        self.canvas.update()

    def add_square(self):
        top_left = Point(400, 100)
        bottom_right = Point(450, 150)
        square = Polygon([top_left, bottom_right], shape_type="square")
        self.canvas.shapes.append(square)
        self.list_shapes.addItem("Kwadrat")
        self.save_history()
        self.canvas.update()

    def delete_shape(self):
        idx = self.list_shapes.currentRow()
        if idx >= 0:
            del self.canvas.shapes[idx]
            self.list_shapes.takeItem(idx)
            self.canvas.selected_index = None
            self.save_history()
            self.canvas.update()

    def select_shape(self, index):
        self.canvas.selected_index = index
        self.canvas.update()

        # Aktualizacja tekstu informacyjnego
        if index >= 0 and index < len(self.canvas.shapes):
            shape = self.canvas.shapes[index]
            if len(shape.points) == 1:
                self.info_label.setText(f"Punkt: ({shape.points[0].x:.1f}, {shape.points[0].y:.1f})")
            else:
                self.info_label.setText(f"Wielokąt: {len(shape.points)} punktów")
        else:
            self.info_label.setText("Wybierz obiekt...")

    def save_history(self):
        # Zapisujemy głęboką kopię kształtów do historii do cofania
        snapshot = json.dumps([shape.to_dict() for shape in self.canvas.shapes])
        self.history.append(snapshot)
        # Limit historii do 20
        if len(self.history) > 20:
            self.history.pop(0)

    def undo(self):
        if len(self.history) < 2:
            QMessageBox.information(self, "Cofnij", "Brak wcześniejszego stanu do cofnięcia.")
            return
        self.history.pop()  # usuwamy obecny
        last = self.history[-1]
        shapes_data = json.loads(last)
        self.canvas.shapes = [Polygon.from_dict(d) for d in shapes_data]
        self.list_shapes.clear()
        for s in self.canvas.shapes:
            if len(s.points) == 1:
                self.list_shapes.addItem("Punkt")
            else:
                self.list_shapes.addItem("Wielokąt")
        self.canvas.selected_index = None
        self.canvas.update()

    def get_selected_shape(self):
        idx = self.canvas.selected_index
        if idx is None or idx < 0 or idx >= len(self.canvas.shapes):
            QMessageBox.warning(self, "Błąd", "Wybierz najpierw obiekt.")
            return None
        return self.canvas.shapes[idx]

    def translate_shape(self):
        shape = self.get_selected_shape()
        if not shape:
            return
        try:
            dx = float(self.input_dx.text())
            dy = float(self.input_dy.text())
        except ValueError:
            QMessageBox.warning(self, "Błąd", "Nieprawidłowe wartości dx lub dy.")
            return
        shape.translate(dx, dy)
        self.save_history()
        self.canvas.update()

    def scale_shape(self):
        shape = self.get_selected_shape()
        if not shape:
            return
        try:
            sx = float(self.input_sx.text())
            sy = float(self.input_sy.text())
        except ValueError:
            QMessageBox.warning(self, "Błąd", "Nieprawidłowe wartości sx lub sy.")
            return
        center = shape.center()
        shape.scale(sx, sy, center)
        self.save_history()
        self.canvas.update()

    def rotate_shape(self):
        shape = self.get_selected_shape()
        if not shape:
            return
        try:
            angle = float(self.input_angle.text())
        except ValueError:
            QMessageBox.warning(self, "Błąd", "Nieprawidłowa wartość kąta.")
            return
        center = shape.center()
        shape.rotate(angle, center)
        self.save_history()
        self.canvas.update()

    def save_to_file(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Zapisz scenę", "", "JSON files (*.json)")
        if filename:
            try:
                data = [shape.to_dict() for shape in self.canvas.shapes]
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
                QMessageBox.information(self, "Zapis", "Zapisano pomyślnie.")
            except Exception as e:
                QMessageBox.warning(self, "Błąd", f"Nie udało się zapisać pliku:\n{e}")

    def load_from_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Wczytaj scenę", "", "JSON files (*.json)")
        if filename:
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
                self.canvas.shapes = [Polygon.from_dict(d) for d in data]
                self.list_shapes.clear()
                for s in self.canvas.shapes:
                    if len(s.points) == 1:
                        self.list_shapes.addItem("Punkt")
                    else:
                        self.list_shapes.addItem("Wielokąt")
                self.canvas.selected_index = None
                self.save_history()
                self.canvas.update()
                QMessageBox.information(self, "Wczytaj", "Wczytano pomyślnie.")
            except Exception as e:
                QMessageBox.warning(self, "Błąd", f"Nie udało się wczytać pliku:\n{e}")

    def on_canvas_mouse_release(self, event):
        # Po zmianie pozycji punktu na canvas, zapisujemy stan
        if self.canvas.dragging_point_index is not None:
            self.save_history()
        self.canvas.dragging_point_index = None
        self.canvas.update()
        QWidget.mouseReleaseEvent(self.canvas, event)

    def import_points(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Wczytaj punkty", "", "JSON files (*.json)")
        if filename:
            try:
                with open(filename, "r") as f:
                    data = json.load(f)

                if isinstance(data, list) and all("points" in shape for shape in data):
                    for shape in data:
                        pts = [Point(p["x"], p["y"]) for p in shape["points"]]
                        if pts:
                            self.canvas.shapes.append(Polygon(pts))
                            if len(pts) == 1:
                                self.list_shapes.addItem("Punkt")
                            else:
                                self.list_shapes.addItem(f"Wielokąt ({len(pts)} pkt)")
                    self.save_history()
                    self.canvas.update()
                    QMessageBox.information(self, "Import", "Dane zaimportowano pomyślnie.")
                else:
                    QMessageBox.warning(self, "Błąd", "Niepoprawny format pliku JSON.")

            except Exception as e:
                QMessageBox.warning(self, "Błąd", f"Nie udało się wczytać pliku:\n{e}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 600)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
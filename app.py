from flask import Flask, render_template, Response, request, redirect, url_for
import face_recognition
import cv2
import threading
import os
app = Flask(__name__)


# 初始化已知人脸
known_images = []
known_names = []
known_dir = "known_faces"

def load_known_faces():
    global known_images, known_names
    known_images = []
    known_names = []

    for filename in os.listdir(known_dir):
        image = face_recognition.load_image_file(os.path.join(known_dir, filename))
        encoding = face_recognition.face_encodings(image)[0]
        known_images.append(encoding)
        known_names.append(os.path.splitext(filename)[0])

load_known_faces()  # 初始化已知人脸

# 创建锁，确保多线程处理帧时的同步
frame_lock = threading.Lock()

# 打开摄像头
camera = cv2.VideoCapture(0)

def camera_thread():
    while True:
        ret, frame = camera.read()
        if ret:
            with frame_lock:
                process_frame(frame)
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


# 初始化Flask上下文
@app.route('/')
def index():
    return render_template('index.html')

# 定义人脸检测和绘制的函数
def process_frame(frame):
    # 降低图像分辨率为原来的 1/2
    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    # 每隔一个视频帧检测人脸
    process_this_frame = True

    if process_this_frame:
        # 检测人脸位置
        face_locations = face_recognition.face_locations(small_frame)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            results = face_recognition.compare_faces(known_images, face_encoding)
            name = "unknown"

            for i, result in enumerate(results):
                if result:
                    name = known_names[i]

            cv2.rectangle(frame, (left * 2, top * 2), (right * 2, bottom * 2), (0, 255, 0), 2)
            font = cv2.FONT_HERSHEY_DUPLEX
            font_scale = 1.5
            font_thickness = 2
            cv2.putText(frame, name, (left * 2 + 6, bottom * 2 - 6), font, font_scale, (255, 0, 0), font_thickness)

# 生成视频流
def generate_frames():
    while True:
        ret, frame = camera.read()
        if ret:
            with frame_lock:
                process_frame(frame)
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# 视频流路由
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# 添加路由：检查人脸识别登录状态
@app.route('/check_login')
def check_login():
    # 检测人脸并判断是否在数据库中
    ret, frame = camera.read()
    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    face_locations = face_recognition.face_locations(small_frame)
    face_encodings = face_recognition.face_encodings(small_frame, face_locations)
    is_recognized = False

    for face_encoding in face_encodings:
        results = face_recognition.compare_faces(known_images, face_encoding)
        if any(results):
            is_recognized = True
            break

    if is_recognized:
        return {'success': True,'message': '登录成功，跳转中...'}
    else:
        return {'success': False, 'message': '登录失败，未匹配到人脸。'}


# 添加路由：上传人脸
@app.route('/upload_face', methods=['POST'])
def upload_face():
    try:
        stop_recognition()  # 先停止人脸识别进程
        image = request.files['image']
        if image:
            image_path = os.path.join(known_dir, image.filename)
            image.save(image_path)
            load_known_faces()  # 重新加载已知人脸
            start_recognition()  # 重新启动人脸识别进程
            return {'success': True, 'message': '人脸上传成功！'}
        else:
            start_recognition()  # 重新启动人脸识别进程
            return {'success': False, 'message': '未选择人脸。'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

# 添加路由：删除指定人脸
@app.route('/delete_face/<string:name>', methods=['POST'])
def delete_face(name):
    try:
        stop_recognition()  # 先停止人脸识别进程
        if name in known_names:
            index = known_names.index(name)
            known_names.pop(index)
            known_images.pop(index)
            image_path = os.path.join(known_dir, f"{name}.jpg")
            os.remove(image_path)
            start_recognition()  # 重新启动人脸识别进程
            return {'success': True, 'message': f'人脸 {name} 删除成功'}
        else:
            start_recognition()  # 重新启动人脸识别进程
            return {'success': False, 'message': '未找到人脸'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def stop_recognition():
    global camera
    try:
        camera.release()
        cv2.destroyAllWindows()
    except Exception as e:
        pass

def start_recognition():
    global camera
    camera = cv2.VideoCapture(0)
    threading.Thread(target=camera_thread).start()


# 添加路由：管理员登录验证
@app.route('/admin_login', methods=['POST'])
def admin_login():
    try:
        data = request.get_json()
        password = data.get('password')

        # 在这里进行管理员密码验证，可以是硬编码的密码或从数据库中获取
        if password == '114514':
            return {'success': True, 'message': '管理员登录成功'}
        else:
            return {'success': False, 'message': '管理员登录失败'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


if __name__ == "__main__":
    app.run(debug=True)



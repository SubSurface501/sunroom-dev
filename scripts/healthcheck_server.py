from flask import Flask
import threading

app = Flask(__name__)

@app.route('/healthz')
def healthz():
    return "OK", 200

def run_health_check_server():
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    # Start the health check server in a separate thread
    health_check_thread = threading.Thread(target=run_health_check_server)
    health_check_thread.daemon = True
    health_check_thread.start()

    # In a real application, you would start your main application logic here.
    # For this example, we'll just wait for the health check thread to finish.
    health_check_thread.join()

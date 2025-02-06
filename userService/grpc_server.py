import grpc
from concurrent import futures
import proto.user_pb2_grpc as user_pb2_grpc
import proto.user_pb2 as user_pb2
from jose import jwt, JWTError
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
ALGORITHM = "HS256"


class AuthService(user_pb2_grpc.AuthServiceServicer):
    def VerifyToken(self, request, context):
        token = request.token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if email is None:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("Invalid token: no subject found")
                return user_pb2.TokenResponse(valid=False)

            return user_pb2.TokenResponse(valid=True)

        except JWTError:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("Invalid or expired token")
            return user_pb2.TokenResponse(valid=False)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_pb2_grpc.add_AuthServiceServicer_to_server(AuthService(), server)
    server.add_insecure_port("[::]:50051")
    print("gRPC User Authentication Service running on port 50051...")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

import socket#导入socket模块 用于创建TCP连接和收发数据
import sys#导入sys模块 用于读取命令行参数和退出程序


if len(sys.argv) not in (3,4):
	print("usage: python wbget.py host path [port]")
	sys.exit(1)#参数个数不足 直接退出 不继续联网
host=sys.argv[1]#第一个参数 服务器域名或者IP
path=sys.argv[2]#第二个参数 请求路径
port=int(sys.argv[3]) if len(sys.argv)==4 else 80
#第三个参数 不传就默认80端口

#构造 HTTP/1.1请求报文	
request = (
    f"GET {path} HTTP/1.1\r\n"#请求行 方法＋路径+HTTP版本
    f"Host: {host}\r\n"#host头
    "Connection: close\r\n"#请求服务器响应后关闭TCP连接
    "\r\n"#空行 表示请求头结束
)

#创建TCP socket
#AF_INET 表示IPv4 .SOCK_STREAM表示TCP
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(10)

#buffer 累积还没拼出完整响应头的数据
buffer = b""
#header_bytes保存响应头，None表示还没找到响应头结束位置
header_bytes = None
#body保存正文 始终是bytes
body = b""
content_length = None
count = 0

try:
    s.connect((host, port)) #与服务器建立TCP连接 触发三次握手
    s.sendall(request.encode()) #保证整个请求发送出去

    while True: #循环接收
        # 最多接收 4096 字节；返回值可能少于 4096。
        data = s.recv(4096)
  	# 结束条件 1：recv 返回 b""，表示对端关闭了连接。
        # 这通常用于没有 Content-Length 的响应；
        # 因为请求里带了 Connection: close，服务器发完会关闭。
        if not data:
            break
        # 统计 recv 次数，并打印本次实际收到多少字节。
        count += 1
        print(f"recv #{count}: {len(data)} bytes")

        # 如果还没有找到响应头结束位置，就先累积到 buffer 里找。
        if header_bytes is None:
            buffer += data
            # HTTP 响应头和正文之间用 \r\n\r\n 分隔。
            pos = buffer.find(b"\r\n\r\n")
            # 找到分隔符，说明响应头已经完整。
            if pos != -1:
		#分隔符之前是响应头
                header_bytes = buffer[:pos]
		#分隔符之后可能已经包含一部分正文，先保存下来
                body = buffer[pos + 4:]
		#HTTP头按Latin-1解码
                header_text = header_bytes.decode("iso-8859-1")
                # 从响应头中解析 Content-Length。
                for line in header_text.split("\r\n")[1:]:
                    if line.lower().startswith("content-length:"):
                        content_length = int(line.split(":", 1)[1].strip())
                        break
        else:
            # 响应头已经解析过，后续收到的数据都是正文。
            body += data
 	# 结束条件 2：如果响应头给出了 Content-Length，
        # 那么 body 收够这个长度就可以停止，不必等服务器关闭。
        # 使用 >= 是因为一次 recv 可能多收到一些字节
        if content_length is not None and len(body) >= content_length:
            break

except socket.timeout:
    print("timeout: no data received within 10 seconds")

finally:
    # 无论成功、超时还是异常，最后都关闭 socket。
    s.close()

# 如果一直没有找到完整的响应头，说明响应不完整或连接提前断开。
if header_bytes is None:
    print("No complete HTTP header received.")
else:
    header_text = header_bytes.decode("iso-8859-1")
    lines = header_text.split("\r\n")

    status_line = lines[0]
    headers = lines[1:]

    print("status line:", status_line)

    parts = status_line.split(" ", 2)
    if len(parts) >= 2:
        print("status code:", parts[1])

    print("headers:")
    for h in headers:
        if h:
            print(h)

    print("body bytes:", len(body))
    print("content length:", content_length)
    print("recv count:", count)

    # 用二进制模式保存正文，保证图片等二进制数据不被文本模式破坏。
    with open("response.html", "wb") as f:
        f.write(body)

    print("saved bytes:", len(body))
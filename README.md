# sender_receiver下面对这四个文件的职责做一个逐一说明，并简要概述它们之间的协作关系。

⸻

1. packet_sim.py

作用：
	•	定义了一个简单的 “模拟数据包” 类 SimPacket，用于在仿真过程中跟踪每个包的关键指标：
	•	发送序号（seq）
	•	发送时间戳（send_ts）
	•	包大小（size_bits）
	•	接收时间戳（recv_ts）
	•	ACK 发送时间戳（ack_send_ts）
	•	ACK 接收时间戳（ack_recv_ts）
	•	提供 to_dict() 方法，把这些信息打平成字典，方便写入 CSV 或其他日志格式。

核心价值： 统一管理和导出每个包的生命周期数据，便于后续统计和可视化。

⸻

2. sim_env.py

作用：
	•	封装了全局仿真环境，包括：
	•	事件队列（event_queue）
	•	当前仿真时间（current_time）
	•	调度函数 schedule(delay, callback, *args)，将任意事件安排到“未来时刻”执行。
	•	解除 sender 和 receiver 之间的循环依赖，让它们都通过同一个环境模块来访问时钟和队列。

核心价值： 提供一个统一的、可重用的离散事件调度框架，让各个模块只需调用 sim_env.schedule() 即可安排后续动作。

⸻

3. cubic_sender.py

作用：
	•	基于 CUBIC 拥塞控制算法，模拟一个 TCP 发送端的全过程：
	1.	发包：根据当前 cwnd 向 receiver 发送 SimPacket
	2.	超时重传：为每个包安排 RTO 计时，并在超时后执行重传和拥塞窗口退避
	3.	接收 ACK：收到 ACK 回调时，更新 RTT 估算（srtt、rttvar）、动态计算新的 RTO，并按 CUBIC 公式调整 cwnd
	4.	日志记录：将每个包的所有时间戳和比特数写入 packet_log.csv，方便离线分析
	•	不直接操作网络，只通过 sim_env.schedule() 调度与 receiver 的交互。

核心价值： 离线仿真 Cubic 算法的拥塞控制行为，并自动产生日志，用于性能评估或调参。

⸻

4. cubic_receiver.py

作用：
	•	模拟一个简单的接收端：
	1.	按时“收到”：由 sim_env 调度触发 receive(seq, send_ts, sender)
	2.	打印日志：记录收到的数据包序号
	3.	发送 ACK：模拟 ACK 的链路延迟后，通过 sim_env.schedule() 回调 sender.ack(...)
	•	只关心按序 ACK，不做乱序缓存或 SACK。

核心价值： 提供最简化的接收确认模型，让发送端能够通过 ACK 事件推动拥塞控制状态机。

⸻

四者协作流程概览
	1.	初始化
	•	cubic_sender.py 创建 CubicSender 与 CubicReceiver，并在环境中安排第一次发包事件。
	2.	发包→收包→ACK
	•	CubicSender.send() 调用 sim_env.schedule() 把“数据包抵达接收端”事件放入队列。
	•	sim_env 推进时钟，触发 CubicReceiver.receive()，再调度“ACK 抵达发送端”事件。
	•	最终调用回 CubicSender.ack()，完成一次往返。
	3.	重传与拥塞控制
	•	如果某个包超过 RTO 未得到 ACK，CubicSender.timeout() 会触发重传并退避窗口。
	•	每次 ACK 或超时后，CubicSender 根据 CUBIC 公式更新 cwnd。
	4.	日志输出
	•	每收到一个 ACK，就把对应 SimPacket 的全生命周期数据写入 packet_log.csv。

这样，你就拥有了一个纯 Python、基于离散事件调度的 Cubic 拥塞控制仿真平台，既能看算法逻辑，又能产出可分析的数据。

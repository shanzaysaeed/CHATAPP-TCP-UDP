from functools import reduce
import sys
from collections import defaultdict
from router import Router
from packet import Packet
from json import dumps, loads
from dijkstar import Graph, find_path


class LSrouter(Router):
    """Link state routing protocol implementation."""

    def __init__(self, addr, heartbeatTime):
        """TODO: add your own class fields and initialization code here"""
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeatTime = heartbeatTime
        self.last_time = 0
        # Hints: initialize local state
        self.g = Graph(undirected=True)
        self.g.add_node(str(addr))
        self.temp = Graph(undirected=True)
        self.temp.add_node(str(addr))
        self.graph = {}
        self.seq_num = {}
        self.graph[addr] = {}
        self.router = {}
        self.comp_state = {}
        self.forwarding_table = {}
        self.ports_dict = {}
        self.port_table = {}
        self.table = {}
        self.seq_num[addr] = 0

    def handlePacket(self, port, packet):
        """TODO: process incoming packet"""
        if packet.isTraceroute():
           
            found = False
            to_send = packet
            destination = to_send.dstAddr

            if destination in self.table:
                while True:
                    if self.table[destination] == self.addr: 
                        break
                    else:
                        if destination == self.addr:
                            break
                        else:
                            next_hop = self.table[destination]
                            destination = next_hop

                if destination in self.g[self.addr]:
                    found = True
                if found:
                    port_to_send = self.g[self.addr][destination]["port"]
                    self.send(port_to_send, packet)
        else:
           
            self.router[self.addr] = self.graph[self.addr]

            ifupdate = False
            content = loads(packet.content)
            addrs = content["add"] if content["add"] else content["reduce"]

            if addrs is not None and addrs["src"] not in self.seq_num:
                self.seq_num[addrs["src"]] = 0
            if addrs is None or self.seq_num[addrs["src"]] >= content["seq_num"]:
                self.dijkstra_algorithm()
                return
            recv_seq_no = content["seq_num"]
            self.seq_num[addrs["src"]] = recv_seq_no

            if addrs["src"] not in self.graph:
                self.graph[addrs["src"]] = {}
                self.router[addrs["src"]] = {}

            if content["add"]: 
                self.type_of_content(addrs,content)
            elif content["reduce"]:
                self.type_of_content(addrs,content)
            else:
                ifupdate = True
            
            if ifupdate:
                self.dijkstra_algorithm()
            else:
                for i in self.router[self.addr]:
                    p = Packet(Packet.ROUTING, self.addr, i, dumps(content))
                    self.send(self.router[self.addr][i]["port"], p)
  
    def handleNewLink(self, port, endpoint, cost):
        """TODO: handle new link"""
        # Hints:
        # update the forwarding table
        # broadcast the new link state of this router to all neighbors
        mini_dict= {"port": port, "cost":cost}
        main_table = { }
        main_table[endpoint] = mini_dict
        self.graph[self.addr][endpoint] = mini_dict
        self.g.add_edge(self.addr, endpoint, main_table[endpoint])
    

        self.port_table[endpoint] = port
        self.ports_dict[port] = endpoint
        self.increase_Seq_no()
        
        content = self.make_content(self.g,endpoint)
        list = self.g[self.addr]
        for neighbour in list:
            port_curr = self.g[self.addr][neighbour]["port"]
            self.send(port_curr, Packet(Packet.ROUTING, self.addr, neighbour, content))

    def handleRemoveLink(self, port):
        """TODO: handle removed link"""

        endpoint= self.ports_dict.get(port)
        del self.graph[self.addr][endpoint]
        del self.g[self.addr][endpoint]

        self.increase_Seq_no()

        redu= {"src": self.addr, "tgt": endpoint}
        content = self.make_content(self.g, endpoint,redu )

        self.send_neighbour(content)

    def handleTime(self, timeMillisecs):
        """TODO: handle current time"""
        if timeMillisecs - self.last_time >= self.heartbeatTime:
            self.last_time = timeMillisecs
            # Hints:
            # broadcast the link state of this router to all neighbors
            content = self.make_content(self.graph)
            self.send_neighbour(content)

    def debugString(self):
        """TODO: generate a string for debugging in network visualizer"""
        return ""


    def type_of_content(self,addrs,content):
        self.graph[addrs["src"]] = content["info"]
        self.router[addrs["src"]] = content["info"]  

    def increase_Seq_no(self):
        self.seq_num[self.addr] = self.seq_num[self.addr] + 1

    def send_neighbour(self,content):
        for neighbor, info in self.graph[self.addr].items():
                p = Packet(Packet.ROUTING, self.addr, neighbor, content)
                self.send(info["port"], p)

    def graph_with_clients(self):
        self.comp_state = {}
        
        for i in self.router:
            self.comp_state[i] = self.router[i]
            for j in self.router[i]:
                if j not in self.router:
                    if j not in self.comp_state:
                        self.comp_state[j] = {}
                    self.comp_state[j][i] = self.router[i][j]
                    
    def make_content(self,graph, endpoint= None, red= None, add = None):
        new_dict= {
        "info": graph[self.addr],
        "add": {"src": self.addr, "tgt": endpoint},
        "reduce": red,
        "seq_num": self.seq_num[self.addr]
        }
        new_dict = dumps(new_dict)

        return new_dict

    def dijkstra_algorithm(self):
        self.graph_with_clients()
        self.table = {}
        N = set()
        D = {}

        for i in self.router:
            N.add(i)
            for j in self.router[i]:
                N.add(j)

        for addr in N:
            if addr != self.addr:
                D[addr] = float("inf") if addr not in self.graph[self.addr] else self.graph[self.addr][addr]["cost"]
            else:
                D[addr] = 0

        length = len(N)
        while(length):
            minimum = min(N, key=lambda x: D[x])
            N.remove(minimum)
            length -= 1
            for i in self.comp_state[minimum]:
                D[i] = min(D[i], D[minimum] + self.comp_state[minimum][i]["cost"])
                if D[minimum] + self.comp_state[minimum][i]["cost"] <= D[i]:
                    self.table[i] = minimum

   
   

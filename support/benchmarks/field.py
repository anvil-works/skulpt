# Field
# Mike

import math

SCW,SCH = 900,250

# helper fn
def distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)


class Vec:
    def __init__(self, x, y, pos=[0,0]):
        self.position = pos
        self.mag = distance([x,y],[0,0])
        self.normal = self.normalized(x,y)
        self.wid = SCH*0.035
    def __str__(self):
        return "Position:%s\nMagnitude:%s\nNormal:%s\nVec:%s\n"%(self.position, self.mag, self.normal, self.get_vec())
    def vec_head(self):
        return [self.position[0]+self.normal[0]*self.mag,
                self.position[1]+self.normal[1]*self.mag]
    def dot(self,other):
        return self.normal[0]*other[0]+self.normal[1]*other[1]
    def get_vec(self):
        h = self.vec_head()
        return [h[0]-self.position[0], h[1]-self.position[1]]
    def normalized(self, x, y):
        return [x/self.mag, y/self.mag]
    def rotate(self, ang):
        new_ang = ang + math.atan2(self.normal[1],self.normal[0])
        self.normal = [math.cos(new_ang), math.sin(new_ang)]
    def draw(self):
        r = int(distance(self.position, b.position))
        col = (255*r/400)


class Vec2:
    def __init__(self, x, y, pos=[0,0]):
        self.position = pos
        self.head = [x,y]
    def magnitude(self):
        return max(distance(self.head,self.position),.000000001)
    def normal(self):
        v = [self.head[0]-self.position[0], self.head[1]-self.position[1]]
        m = self.magnitude()
        return [v[0]/m, v[1]/m]

a = []
for y in range(0,SCH,int(SCH*.06)+2):
    for x in range(0,SCW,int(SCW*.06)+2):
        a.append(Vec(35,0,[x,y]))

b = Vec(5.2,5.5,[50,50])

c = Vec2(b.position[0],b.position[1], a[0].position)
c.head = b.position

def update():
    #draw field
    [pt.draw() for pt in a]
    #update rotations
    for pt in a:
        c.position = pt.position
        d = 900/c.magnitude()**2
        cn = c.normal()
        theta = pt.dot([cn[1], -cn[0]])
        pt.rotate(d*theta)
    #update ball
    b.position[0] = min(max(b.position[0]+b.normal[0]*b.mag,0),SCW)
    b.position[1] = min(max(b.position[1]+b.normal[1]*b.mag,0),SCH)
    if b.position[0] == 0 or b.position[0] == SCW:
        b.normal[0] = -b.normal[0]
    if b.position[1] == 0 or b.position[1] == SCH:
        b.normal[1] = -b.normal[1]



# Each call starts from the same simulation state. Keep the original grid,
# draw comprehension, vector methods and bouncing ball; run enough frames to
# exercise warmed JavaScript and allocation/GC, not just module startup.
def benchmark():
    global b, c
    for pt in a:
        pt.normal = [1.0, 0.0]
    b = Vec(5.2, 5.5, [50, 50])
    c = Vec2(b.position[0], b.position[1], a[0].position)
    c.head = b.position
    for frame in range(200):
        update()
    return [b.position[0], b.position[1],
            sum(pt.normal[0] for pt in a), sum(pt.normal[1] for pt in a)]

# Keep the same reset/checksum behaviour in each replay of the longer fixture.
benchmark_once = benchmark

def benchmark_long():
    checksum = 0.0
    result = None
    for replay in range(30):
        result = benchmark_once()
        checksum += result[2]
    return [30, checksum, result]

if __name__ == "__main__":
    print(benchmark())

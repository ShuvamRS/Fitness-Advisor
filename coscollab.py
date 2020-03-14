from scipy import spatial
from random import randrange
from math import sqrt, pow

'''
Created 10 random users with 10 activities ranging from 0-100 frequency
users = []
for i in range(10):
    user = []
    for j in range(10):
        user.append(randrange(100))
    users.append(user)

print(users)
'''

# Hard-coded users
users = [[14, 84, 36, 24, 7, 23, 7, 28, 56, 43], [98, 44, 35, 45, 64, 82, 96, 35, 2, 79], [10, 82, 18, 80, 4, 62, 83, 15, 10, 91], [2, 18, 6, 80, 3, 18, 37, 47, 91, 15], [21, 31, 4, 23, 96, 59, 25, 12, 23, 36], [73, 31, 84, 9, 48, 12, 3, 41, 52, 10], [34, 94, 35, 91, 11, 83, 45, 23, 98, 53], [35, 3, 12, 99, 39, 11, 2, 30, 98, 1], [48, 62, 1, 50, 29, 30, 71, 48, 6, 80], [90, 25, 95, 17, 45, 23, 55, 28, 7, 33]]

# Uses cosine similarity with one user vs all the rest
min_sims = []
for i in range(10):
    min_sim = []
    for j in range(10):
        if i == j:
            min_sim.append(999)
        else:
            min_sim.append(spatial.distance.cosine(users[i], users[j]))
    min_sims.append(min_sim)

#print(min_sims)

# Finds the min cos_sim for each user
sim_user = []
for m in min_sims:
    sim_user.append(m.index(min(m)))

#print(sim_user)

# Finds max difference between the most similar users' activities
rec_act = []
for s in range(10):
    max_dif = []
    for a in range(10):
        max_dif.append(sqrt(pow(users[s][a] - users[sim_user[s]][a], 2)))

    rec_act.append(max_dif.index(max(max_dif)))

# Activity # recommended to user (index)
# For example: rec_act[0] = 5, so Activity 6 recommended to User 1
print(rec_act)


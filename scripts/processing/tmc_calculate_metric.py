# cca = ["cubic", "reno", "hstcp", "bic", "htcp"]
# thuput_mmw = [468.4, 406.2, 581.5, 482.0, 561.0]
# udp_mmw = 1013.0

# for i, e in enumerate(thuput_mmw):
#     v = round(100 * e / udp_mmw, 2)
#     print(f"{v}\\%")


# # HO freq
# ho_nums = [749, 230, 91, 100, 79]
# ho_int = [22.1, 21.35, 16.43, 22.28, 15.64]

# avg_ho_int = 0
# for i in range(len(ho_int)):
#     avg_ho_int += ho_nums[i] * ho_int[i]
# avg_ho_int /= sum(ho_nums)
# print("HO avg interval", avg_ho_int)
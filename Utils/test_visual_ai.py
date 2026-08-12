from Utils.visual_ai import analyze_visual_difference

result = analyze_visual_difference(

    reference_image=r"D:\Automation_Framework\Reports\Smoke_20260715_181411\comparison\SC_02\Home\reference_SC02_Home_page_top.png",

    actual_image=r"D:\Automation_Framework\Reports\Smoke_20260715_181411\comparison\SC_02\Home\actual_SC02_Home_page_top.png",

    difference_image=r"D:\Automation_Framework\Reports\Smoke_20260715_181411\comparison\SC_02\Home\diff_SC02_Home_page_top.png",

    similarity=58.07,

    difference_count=68

)

print(result)
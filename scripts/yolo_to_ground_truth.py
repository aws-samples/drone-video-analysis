import os

import imagesize
import yaml
import json
import time

yolo_folder = "<path_to_downloaded_yolo_v5_pytorch_dataset>"
s3_bucket = "s3://<bucket_name>"
base_bucket_path = f"{s3_bucket}/<path_to_downloaded_yolo_v5_pytorch_dataset>"
output_dir = "<output-directory>"

"""
Each directory in dataset is in different splits; test, train and valid
Inside each directory there are two folders: images and labels
Labels folder contains the yolo labels, each text file with the same name as the image
Images folder contains the images

https://blog.paperspace.com/train-yolov5-custom-data/
Each .txt file contains lines with class_id center_x center_y width height

We can assume images are in the base_bucket in AWS cloud


"""


def yolo_line_to_ground_truth(lines, class_map, file_path, img_width=720, img_height=720):
    """
    Sample ground truth line output:
    {"source-ref":"s3://bucket/mp4-frame26.jpg","detections":{"image_size":[{"width":img_width,"height":img_height,"depth":img_depth}],"annotations":[{"class_id":0,"top":238,"left":1050,"height":404,"width":870}]},"detections-metadata":{"objects":[{"confidence":0}],"class-map":{"0":"label0"},"type":"groundtruth/object-detection","human-annotated":"yes","creation-date":"2022-07-24T06:36:34.492316","job-name":"jobName1"}}
    Ideally we need the source-ref and detections, annotations, class-map, type
    """

    #     This function will convert a yolo line to ground truth format
    #     Each line is in the format: class_id center_x center_y width height
    #     We need to convert this to top, left, height, width
    #     We also need to convert the class_id to the class_name
    gt_line = dict()
    # source-ref is base_bucket_path + file_path
    gt_line["source-ref"] = os.path.join(s3_bucket, file_path)
    gt_line["detections"] = dict()
    gt_line["detections"]["image_size"] = [{"width": img_width, "height": img_height, "depth": 3}]
    gt_line["detections"]["annotations"] = []
    # add the detections based on the line in yolo format
    for line in lines:
        line = line.strip()
        line_components = line.split(" ")
        if len(line_components) != 5:
            print(f"🔥 invalid values provided for labels {file_path}")
            continue
        class_id, center_x, center_y, width, height = line_components
        class_id = int(class_id)
        center_x = float(center_x)
        center_y = float(center_y)
        width = float(width)
        height = float(height)

        # Convert to top, left, height, width
        top = (center_y - height / 2) * img_height
        left = (center_x - width / 2) * img_width
        height = height * img_height
        width = width * img_width

        gt_line["detections"]["annotations"].append(
            {
                "class_id": class_id,
                "top": top,
                "left": left,
                "height": height,
                "width": width,
            }
        )

    gt_line["detections-metadata"] = dict()
    full_confidence = {"confidence": 1}
    gt_line["detections-metadata"]["objects"] = [full_confidence for _ in
                                                 range(len(gt_line["detections"]["annotations"]))]
    gt_line["detections-metadata"]["class-map"] = class_map
    gt_line["detections-metadata"]["type"] = "groundtruth/object-detection"
    gt_line["detections-metadata"]["human-annotated"] = "yes"
    # now date in "2022-07-24T06:36:34.492316" format
    gt_line["detections-metadata"]["creation-date"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    gt_line["detections-metadata"]["job-name"] = "automated_conversion"

    print(json.dumps(gt_line, indent=4))
    return gt_line


def process_directory(directory, class_map):
    labels_dir = os.path.join(directory, "labels")
    #     This directory will contain images and labels folder. We will process each of these
    gt_lines = []
    for label_file in os.listdir(labels_dir):
        #         Read the label file
        label_file_path = os.path.join(labels_dir, label_file)
        with open(label_file_path) as f:
            lines = f.readlines()
            if lines:
                img_file_path = os.path.join(directory, "images", label_file.replace(".txt", ".jpg"))
                width, height = imagesize.get(img_file_path)
                print("computed width and height", width, height)
                gt_line = yolo_line_to_ground_truth(lines, class_map, img_file_path, img_width=width, img_height=height)
                gt_lines.append(gt_line)

    return gt_lines


def process(yolo_path, bucket_path, output_path):
    print("Processing yolo data")
    print(yolo_path)

    #     This function will read the yolo dataset format and convert it to ground truth format
    #     The dataset contains a test, train and valid folder and a data.yaml with classes
    # Create a class map
    class_map = {}
    with open(os.path.join(yolo_path, "data.yaml")) as f:
        #         Convert yaml to json
        data = yaml.safe_load(f, Loader=yaml.FullLoader)
        for i, class_name in enumerate(data["names"]):
            class_map[i] = class_name

    print("Classmap: " + json.dumps(class_map, indent=4))
    train_gt = process_directory(os.path.join(yolo_path, "train"), class_map)
    valid_gt = process_directory(os.path.join(yolo_path, "valid"), class_map)
    # test_gt = process_directory(os.path.join(yolo_path, "test"), class_map)
    all_gt = train_gt + valid_gt

    with open(os.path.join(f"{yolo_folder}-output--yolo--to--gt.output.manifest"), "w") as f:
        #         output in json lines format
        f.write("\n".join([json.dumps(line) for line in all_gt]))


if __name__ == "__main__":
    process(yolo_folder, base_bucket_path, output_dir)

#!/bin/bash

code_name=pvpng_autoview.py
machines=("ishtar" "loki" "hades" "attila" "marduk" "heise")
# machines=("ishtar")

list_dir=/dagon1/achitsaz/runfebio/accept_runs_cases.txt
use_test_case=true  # Set to false to read from file

if [ "$use_test_case" = true ]; then
    raw_cases=("a06161.1")
else
    if [ -f "$list_dir" ]; then 
        mapfile -t raw_cases < "$list_dir"
    else
        echo "ERROR: Case list not found at: $list_dir"
        exit 1
    fi
fi
# Generate 4 jobs per case
jobs=()
for case in "${raw_cases[@]}"; do
    jobs+=("$case 1 colormap_png.json 4 ")
    jobs+=("$case 2 colormap_png.json 4")
    jobs+=("$case 1 colormap_anim.json 90 --anim")
    jobs+=("$case 2 colormap_anim.json 90 --anim")
done

total_jobs=${#jobs[@]}
echo "Total # of jobs to run: $total_jobs"
echo "Total # of machines: ${#machines[@]}"

run_case_on_machine () {
    local machine=$1
    local case_id=$2
    local msa=$3
    local colormap=$4
    local nframes=$5
    shift 5
    local extra_opts=$@

    local pvpython_dir=/dagon1/achitsaz/app/ParaView-5.13.3-osmesa-MPI-Linux-Python3.10-x86_64/bin/pvpython
    local case_dir=/dagon1/achitsaz/runfebio
    local code_dir=/dagon1/achitsaz/FEBio/autopng

    local command="cd $case_dir/$case_id/pst.$msa/ && unset DISPLAY && nohup $pvpython_dir $code_dir/$code_name stress_analysis_0.vtk ../msa.$msa/checkinput_0.vtk $code_dir/$colormap $nframes --outdir ./render --pf $code_dir/pf.Script $extra_opts > render.log 2>&1 &"

    echo "-> Dispatching: $case_id with pst.$msa and $colormap on $machine"

    if [ "$machine" == "ishtar" ]; then
        eval "$command"
    else
        ssh "$machine" "$command" &
    fi
}

while [ ${#jobs[@]} -gt 0 ]; do
    echo "* Waiting for machine availability..."
    machine_found=0

    for machine in "${machines[@]}"; do
        if [ "$machine" == "ishtar" ]; then
            running_task=$(pgrep pvpython-real | wc -l)
        else
            running_task=$(ssh "$machine" "pgrep pvpython-real | wc -l")
        fi

        if [ "$running_task" -eq 0 ]; then
            machine_found=1

            # Get and remove first job
            IFS=' ' read -r case_id msa colormap nframes extra_opts <<< "${jobs[0]}"
            jobs=("${jobs[@]:1}")

            run_case_on_machine "$machine" "$case_id" "$msa" "$colormap" "$nframes" $extra_opts
            break
        fi
    done

    if [ $machine_found -eq 0 ]; then
        sleep 1m
    else
        sleep 10
    fi
done

echo "✅ All jobs dispatched!"

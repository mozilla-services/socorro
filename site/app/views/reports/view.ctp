<h1 id="report-header" class="first"><?php print $report["product"] . " " . $report["version"] . " Crash Report [@ " . $report["signature"] . " ]"; ?></h1>
   <div id="report-header-details">ID: <span><?php print $report["uuid"]; ?></span><br> Signature: <span><?php print $report["signature"]; ?></span></div>
   <div id="report-index" class="flora">

    <ul>
     <li><a href="#details"><span>Details</span></a></li>
     <li><a href="#frames"><span>Frames</span></a></li>
     <li><a href="#modules"><span>Modules</span></a></li>
     <li><a href="#rawdump"><span>Raw Dump</span></a></li>
    </ul>
    <div id="details">
     <table class="list record">
      <tr class="odd">
       <th>Signature</th><td><?php print $report["signature"]; ?></td>
      </tr>
      <tr class="even">
       <th>UUID</th><td><?php print $report["uuid"]; ?></td>
      </tr>

      <tr class="odd">
       <th>Time</th><td><?php print $report["date"]; ?><td>
      </tr>
      <tr class="even">
       <th>Uptime</th><td><?php print $report["uptime"]; ?></td>
      </tr>
      <tr class="odd">

       <th>Product</th><td><?php print $report["product"]; ?></td>
      </tr>
      <tr class="even">
       <th>Version</th><td><?php print $report["version"]; ?></td>
      </tr>
      <tr class="odd">
       <th>Build ID</th><td><?php print $report["build"]; ?></td>

      </tr>
      <tr class="even">
       <th>OS</th><td><?php print $report["os_name"]; ?></td>
      </tr>
      <tr class="odd">
       <th>OS Version</th><td><?php print $report["os_version"]; ?></td>
      </tr>

      <tr class="even">
       <th>CPU</th><td><?php print $report["cpu_name"]; ?></td>
      </tr>
      <tr class="odd">
       <th>CPU Info</th><td><?php print $report["cpu_info"]; ?></td>
      </tr>
      <tr class="even">

       <th>Crash Reason</th><td><?php print $report["reason"]; ?></td>
      </tr>
      <tr class="odd">
       <th>Crash Address</th><td><?php print $report["address"]; ?></td>
      </tr>
      <tr class="even">
       <th>Comments</th><td><?php print $report["comments"]; ?></td>
      </tr>
    </table>
   </div>
   <div id="frames">
   </div>
   <div id="modules">
   </div>
   <div id="rawdump">

   </div>
  </div>

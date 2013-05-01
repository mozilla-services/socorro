.. index:: usinggit

.. _usinggit-chapter:


Working with Git and GitHub
===========================

Using Git and GitHub can be tricky.  The guide on this page will help you do 
things correctly and in the right order, to avoid hand-wringing and cursing.
The sections should be followed in order: first setup GitHub, then setup Git,
before you start developing.  This guide assumes you are using a command line
interface in a *nix environment like OS X or Ubuntu.

.. _how-to-setup-github:

How to setup GitHub
-------------------
* If you don't already have a GitHub account, register for one.  Choose a 
  username you like, since one's GitHub is often considered a programmer's 
  professional portfolio.
* Setup your SSH key.  The guide in GitHub's documentation, 
  `Generating SSH Keys <https://help.github.com/articles/generating-ssh-keys>`_ 
  , is highly recommended.  
* Here is a rough outline of how to setup your ssh key:
    * Check if you already have an SSH key on your computer.  If not, or if 
      you want a new one, generate an SSH key using the command::

        ssh-keygen -t rsa -C "username@email_provider.com"

    * Login to your GitHub account and find the setting for SSH keys.  Add 
      the public SSH key that is on your local computer to the GitHub account.
    * Test your setup by running the command:: 
 
        ssh -T git@github.com

    * You may be asked to verify the authenticity of the `github.com` website 
      and/or asked for your SSH key passphrase.  This is normal.
    * If you are successful, you will see a message like::

        Hi username! You've successfully authenticated, but GitHub does not provide shell access.

    * If you are not successful, you will see a `Permission denied (public key)`
      error.  In this case, you'll have to retrace your steps and check that 
      you did everything correctly.  Some things to try/check: 

      - Is the key listed on GitHub actually one of the keys on your local 
        computer?
      - Did you copy and paste your key into you GitHub account correctly?
      - Are you running a virtual machine?  Make sure the key you want is in 
        the right place.
      - If all else fails, try rebooting. 
* Fork the repository you are interested in.  Go to the GitHub page of the 
  project (for example `https://github.com/mozilla/socorro`) and click on the 
  button "Fork" in the upper-righthand part of the page.
* Congratulations, you are the proud owner of a copy of this repository!  But
  this repository only exists on GitHub, so you'll have to get a copy on your
  local computer.  The next section describes how to do this.

.. _how-to-setup-git:

How to setup Git
----------------
* Now you need to setup Git and clone the repository onto your computer.
* If you don't have Git, you can download it from the `official Git website <http://git-scm.com/downloads>`_ 
  and install it.  Follow the instructions from the Git website for your
  particular operating system.
* Configure your git information, if you have not already done so.  The most
  basic information you need to setup is your name, email, and editor.  Run the
  following commands:: 

    git config --global user.name "first_name last_name"
    git config --global user.email user@email_provider.com
    git config --global core.editor name_of_editor

  Make sure the email you give is listed in your GitHub account.  The 
  `core.editor` is the editor that is used for writing your commit messages.  
  The editor can be `vi`, `vim`, `emacs`, whatever you like.  The `--global` 
  option sets these as the default.  You can use these commands without the
  global option to override the default.  Finally, check that the configuration
  is correct by running `git config --list` 
* In your browser, open up your GitHub account and navigate to the page
  containing the repository you forked.  There should be a link listed
  at the top of the page with three buttons to the left.  The buttons are
  labeled `HTTP`, `SSH`, and `Git Read-Only`.  The one you want is `SSH`,
  so that you can authenticate access to your GitHub account with your SSH
  key (see :ref:`previous section <how-to-setup-github>`).  So click on the 
  `SSH` button and make note of this link.  (Definitely don't use the 
  `Git Read-Only` link, since you want write access for your commits!)
* Navigate to whatever directory you would like to contain the local 
  repository.  Some people like to use their home directory.  In that case,
  do `cd ~/`
* On your command line, run `git clone :link` where `:link` is the address
  you got from GitHub in the previous step.  To clone Socorro, your command
  will probably be look like::

    git clone git@github.com:username/socorro.git       

.. _developing-with-git-and-github:

Developing with Git and GitHub
------------------------------
* At this point, you should have 3 repositories
    * The master repository for the project (named `mozilla` if you cloned the
      Socorro repository; this is the remote master branch)
    * The forked repository on your GitHub account (usually named the `origin`
      branch; this is also a remote repository)
    * The local repository on your hard drive (usually named the `master` 
      branch; this is the local master branch)
* In general, when you are developing, you want to follow this workflow:
    1. Update your local repository with changes from the remote master branch
    2. Locally checkout a new branch with a name describing the feature or
       bug you are working on
    3. Work on files in your local repository
    4. When you are satisfied with your changes, commit them.
    5. Push your changes from your local repo to your forked repo.
    6. Pull the changes from your forked repo to the master.
* First, check on your setup by running `git remote -v` to list your branches
  and their associated URLs.  Your output should look something like this::

    mozilla	https://github.com/mozilla/socorro (fetch)
    mozilla	https://github.com/mozilla/socorro (push)
    origin	git@github.com:username/socorro.git (fetch)
    origin	git@github.com:username/socorro.git (push)

  `mozilla` is the name of the remote master branch.  We forked the master into 
  a copy on your GitHub account.  The forked branch is named `origin` 
* Now we'll go through the steps in more detail.  
    1. To update your local repository with changes from the master, do the
       following commands in order::

         git remote update
         git checkout master
         git pull mozilla master
       
       The first command downloads updates from the remote repositories, the
       second command switches you to your local master branch, and the third
       command pulls changes from the remote master to your local master.
    2. So now you are almost ready to start working... but not just yet!  You
       don't want to work on your local master branch.  So "switch" to a new
       local branch (sometimes called a feature branch) by running the command
       `git checkout -b :branchname` where you'll want to use a descriptive 
       name for `:branchname`

       A common convention is to use a branchname of the form `bug######-short-description`,
       for example::

         git checkout -b bug867558-doc-git

    3. Now you can work on the files in your local repository to your heart's
       content.
    4. When you are satisfied with your changes or additions, commit them.  
       First, run `git status` to see which files you modified and if git is 
       tracking them.  For example, you might see something like::

         user@~/socorro/docs$ git status
         # On branch bug867558-doc-git
         # Untracked files:
         #   (use "git add <file>..." to include in what will be committed)
         #
         #	../.virtualenv/
         #	usinggit.rst
         #	../exploitable/
         #	../myscript
         #	../pip-cache/
         nothing added to commit but untracked files present (use "git add" to track)
     
       It says there's `nothing added to commit`, so we need to add files to be
       tracked.  To do so, use the command `git add :filename`, for example::      
       
         git add docs/usinggit.rst
       
       If you have multiple files to commit, repeat `git add :filename` for 
       each file.
       
       Check that the files have been labeled as ready to commit by running
       `git status` again. 

       Finally, run `git commit` to actually commit the files.  Type in a useful 
       message, describing what feature you added or bug you fixed and be sure 
       to mention the bug number like `bug#######`.
    5. You are ready to push the changes from your local repository to your
       forked remote repository.  To do so, use the command `git push origin :branchname`

       So an example would be::

         git push origin bug867558-doc-git
       
       After you do the push, point your browser to your GitHub account.  You
       should see a status update saying something like `user pushed to bug867558-doc-git at user/socorro` 
    6. In your GitHub account, navigate to the page for your forked repository.
       In the upper righthand part of the page, there is a button labeled 
       "Pull Request" (not to be confused with the tab "Pull Requests").  Click 
       on that and a new screen will pop up.  You should see a base repo and 
       base branch on the left, a head repo and head branch on the right, with
       an error pointing from the right to the left.  The base repo and branch 
       should be `mozilla/socorro` and `master` and the head repo and branch 
       should be `user/socorro` and whatever you named your feature branch.  
       You are pulling your changes from your forked repo to the remote master 
       at Mozilla.  Confirm the pull request and you are done!

       Thanks for contributing!

.. _troubleshooting:

Troubleshooting
---------------
* Check your git configuration by running `git config --list`
* Run `git remote -v` to list the remote branches and their associated URLs.
* Run `git status` to see what branch you're on and what files Git is tracking.
* Run `git branch` to list all the branches.  The branch with `*` next to it is
  your current branch.
* If you are ready to push changes, you can run `git push` with the `--dry-run` 
  option to see what would happen if you ran your `git push` command.
* If you didn't follow the steps described above, you may have trouble.  In
  particular, a common mistake is to clone the master repository from the 
  project's official GitHub repo directly.  If you then fork the master repo
  to your personal GitHub account later, you will have two repos with separate 
  histories.  GitHub will then complain when you try to push changes to your 
  remote repository.  The error message might contain something like::

    To prevent you from losing history, non-fast-forward updates were rejected
    Merge the remote changes (e.g. 'git pull') before pushing again.  See the
    'Note about fast-forwards' section of 'git push --help' for details.

  This error message says that there are changes on the remote branch that you 
  don't have locally yet.  Contact your local `git` expert for help.

